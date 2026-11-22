*** Settings ***
Library    SSHLibrary
Library    Collections
Suite Teardown    Remove PostgreSQL fixtures

*** Variables ***
${PG_IMAGE}    ghcr.io/geniusdynamics/postgresql19c:0.9.0
${HOST1}    warpgate-pg1.example.org
${HOST2}    warpgate-pg2.example.org
${pg_id}    ${EMPTY}
${wg1}    ${EMPTY}
${wg2}    ${EMPTY}

*** Keywords ***
Run node command
    [Arguments]    ${command}
    ${out}    ${err}    ${rc} =    Execute Command    ${command}    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0    ${out} ${err}
    RETURN    ${out}

Install module
    [Arguments]    ${image}
    ${out} =    Run node command    add-module ${image} 1
    ${id} =    Evaluate    ast.literal_eval($out)['module_id']    ast
    RETURN    ${id}

Configure
    [Arguments]    ${id}    ${host}    ${extra}
    Run node command    api-cli run module/${id}/configure-module --data '{"host":"${host}","http2https":true,"lets_encrypt":false${extra}}'

Warpgate admin API
    [Documentation]    Log in as the Warpgate admin of ${id} and call the admin API
    [Arguments]    ${id}    ${host}    ${method}    ${path}    ${body}=${EMPTY}
    ${script} =    Catenate    SEPARATOR=\n
    ...    set -e
    ...    jar=$(mktemp)
    ...    trap "rm -f $jar" EXIT
    ...    c="curl -ksf -c $jar -b $jar --resolve $1:443:127.0.0.1 -H Content-Type:application/json"
    ...    printf "{\\"username\\":\\"admin\\",\\"password\\":\\"%s\\"}" "$5" | $c -o /dev/null -d @- "https://$1/@warpgate/api/auth/login"
    ...    if [ -n "$4" ]; then $c -X "$2" -d "$4" "https://$1/@warpgate/admin/api$3"; else $c -X "$2" "https://$1/@warpgate/admin/api$3"; fi
    # Members of a cluster share the users of the instance that created it
    ${password} =    Run node command    runagent -m ${wg1} sh -c '. ./passwords.env && printf %s "$WARPGATE_ADMIN_PASSWORD"'
    ${b64} =    Evaluate    base64.b64encode($script.encode()).decode()    base64
    ${out} =    Run node command    runagent -m ${id} sh -c "$(echo ${b64} | base64 -d)" sh ${host} ${method} ${path} '${body}' ${password}
    RETURN    ${out}

Role names
    [Arguments]    ${id}    ${host}
    ${out} =    Warpgate admin API    ${id}    ${host}    GET    /roles
    ${names} =    Evaluate    [r["name"] for r in json.loads($out)]    json
    RETURN    ${names}

Admin login works
    [Arguments]    ${id}    ${host}
    Role names    ${id}    ${host}

Remove PostgreSQL fixtures
    FOR    ${id}    IN    ${wg2}    ${wg1}    ${pg_id}
        IF    $id
            Execute Command    remove-module --no-preserve ${id}
        END
    END

*** Test Cases ***
Install PostgreSQL and Warpgate
    ${id} =    Install module    ${PG_IMAGE}
    Set Suite Variable    ${pg_id}    ${id}
    Run node command    api-cli run module/${pg_id}/configure-module --data '{"role":"standalone"}'
    ${id} =    Install module    ${IMAGE_URL}
    Set Suite Variable    ${wg1}    ${id}
    Configure    ${wg1}    ${HOST1}    ${EMPTY}
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${wg1}    ${HOST1}

Create data in SQLite
    Warpgate admin API    ${wg1}    ${HOST1}    POST    /roles    {"name":"robot-migrated"}
    ${names} =    Role names    ${wg1}    ${HOST1}
    List Should Contain Value    ${names}    robot-migrated

Switch to PostgreSQL keeps the data
    Configure    ${wg1}    ${HOST1}    ,"database":{"mode":"postgresql19c","instance":"${pg_id}"},"cluster":{"mode":"create"}
    ${out} =    Run node command    api-cli run module/${wg1}/get-configuration
    ${db} =    Evaluate    json.loads($out)["database"]    json
    Should Be Equal    ${db}[mode]    postgresql19c
    Should Be True    ${db}[password_set]
    Should Not Contain    ${out}    PGPASSWORD
    ${mode} =    Run node command    runagent -m ${wg1} stat -c %a database.env
    Should Be Equal    ${mode}    600
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${wg1}    ${HOST1}
    ${names} =    Role names    ${wg1}    ${HOST1}
    List Should Contain Value    ${names}    robot-migrated
    ${url} =    Run node command    runagent -m ${wg1} sh -c 'podman unshare cat "$(podman volume inspect --format "{{.Mountpoint}}" data)/.ns8-warpgate.yaml"'
    Should Contain    ${url}    postgres://
    ${password} =    Run node command    runagent -m ${wg1} sh -c '. ./database.env && printf %s "$PGPASSWORD"'
    Should Not Contain    ${url}    ${password}

Second instance joins and shares the database and host key
    ${id} =    Install module    ${IMAGE_URL}
    Set Suite Variable    ${wg2}    ${id}
    Run node command    api-cli run module/${wg1}/set-peer-access --data '{"peer":"${wg2}","allowed":true}'
    Configure    ${wg2}    ${HOST2}    ,"database":{"mode":"postgresql19c","instance":"${pg_id}"},"cluster":{"mode":"join","peer":"${wg1}"}
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${wg2}    ${HOST2}
    ${names} =    Role names    ${wg2}    ${HOST2}
    List Should Contain Value    ${names}    robot-migrated
    Warpgate admin API    ${wg2}    ${HOST2}    POST    /roles    {"name":"robot-shared"}
    ${names} =    Role names    ${wg1}    ${HOST1}
    List Should Contain Value    ${names}    robot-shared
    ${key1} =    Warpgate admin API    ${wg1}    ${HOST1}    GET    /ssh/own-keys
    ${key2} =    Warpgate admin API    ${wg2}    ${HOST2}    GET    /ssh/own-keys
    Should Be Equal    ${key1}    ${key2}

An unapproved instance cannot join
    ${out}    ${rc} =    Execute Command    api-cli run module/${wg1}/admit-peer --data '{"module_id":"${pg_id}"}'    return_rc=True
    Should Not Be Equal As Integers    ${rc}    0
