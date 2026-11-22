*** Settings ***
Library    SSHLibrary
Library    Collections
Suite Teardown    Remove recordings fixtures

*** Variables ***
# MinIO no longer publishes images on Docker Hub: rclone serves an
# S3-compatible API from a directory (each top-level folder is a bucket)
${S3_IMAGE}    docker.io/rclone/rclone:1.75.2
${S3_PORT}    19000
${S3_KEY}    robot-access-key
${S3_SECRET}    robot-secret-key-2026
${S3_BUCKET}    warpgate-recordings
${HOST}    warpgate-rec.example.org
${UPGRADE_HOST}    warpgate-upgrade.example.org
${PREVIOUS_IMAGE}    ghcr.io/geniusdynamics/warpgate:1.3.0
${wg}    ${EMPTY}
${old}    ${EMPTY}
${s3_endpoint}    ${EMPTY}

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
    [Arguments]    ${id}    ${host}    ${extra}=${EMPTY}
    Run node command    api-cli run module/${id}/configure-module --data '{"host":"${host}","http2https":true,"lets_encrypt":false${extra}}'

Configuration of
    [Arguments]    ${id}
    ${out} =    Run node command    api-cli run module/${id}/get-configuration
    ${config} =    Evaluate    json.loads($out)    json
    RETURN    ${config}    ${out}

Warpgate admin API
    [Documentation]    Log in as the Warpgate admin of ${id} and call the admin API
    [Arguments]    ${id}    ${host}    ${method}    ${path}    ${body}=${EMPTY}
    ${script} =    Catenate    SEPARATOR=\n
    ...    set -e
    ...    jar=$(mktemp)
    ...    trap "rm -f $jar" EXIT
    ...    c="curl -ksf -c $jar -b $jar --resolve $1:443:127.0.0.1 -H Content-Type:application/json"
    ...    . ./passwords.env
    ...    printf "{\\"username\\":\\"admin\\",\\"password\\":\\"%s\\"}" "$WARPGATE_ADMIN_PASSWORD" | $c -o /dev/null -d @- "https://$1/@warpgate/api/auth/login"
    ...    if [ -n "$4" ]; then $c -X "$2" -d "$4" "https://$1/@warpgate/admin/api$3"; else $c -X "$2" "https://$1/@warpgate/admin/api$3"; fi
    ${b64} =    Evaluate    base64.b64encode($script.encode()).decode()    base64
    ${out} =    Run node command    runagent -m ${id} sh -c "$(echo ${b64} | base64 -d)" sh ${host} ${method} ${path} '${body}'
    RETURN    ${out}

Admin login works
    [Arguments]    ${id}    ${host}
    Warpgate admin API    ${id}    ${host}    GET    /parameters

Recordings storage of
    [Arguments]    ${id}    ${host}
    ${out} =    Warpgate admin API    ${id}    ${host}    GET    /parameters
    ${storage} =    Evaluate    json.loads($out)["recordings_storage"]    json
    RETURN    ${storage}

Secret backends of
    [Arguments]    ${id}    ${host}
    ${out} =    Warpgate admin API    ${id}    ${host}    GET    /secret-backends
    ${backends} =    Evaluate    json.loads($out)    json
    RETURN    ${backends}

Configure fails with
    [Arguments]    ${id}    ${extra}    ${code}
    ${out}    ${err}    ${rc} =    Execute Command
    ...    api-cli run module/${id}/configure-module --data '{"host":"${HOST}","http2https":true,"lets_encrypt":false${extra}}'
    ...    return_stderr=True    return_rc=True
    Should Not Be Equal As Integers    ${rc}    0
    Should Contain    ${out}${err}    ${code}

Remove recordings fixtures
    FOR    ${id}    IN    ${wg}    ${old}
        IF    $id
            Execute Command    remove-module --no-preserve ${id}
        END
    END
    Execute Command    podman rm -f robot-s3
    Execute Command    podman volume rm -f robot-s3

*** Test Cases ***
Start an S3-compatible service
    ${ip} =    Run node command    redis-cli --no-auth-warning hget node/1/vpn ip_address
    Set Suite Variable    ${s3_endpoint}    http://${ip}:${S3_PORT}
    Run node command    podman volume create --ignore robot-s3
    Run node command    podman run --rm --volume robot-s3:/data:Z --entrypoint mkdir ${S3_IMAGE} -p /data/${S3_BUCKET}
    Run node command    podman run -d --replace --name robot-s3 --volume robot-s3:/data:Z --publish ${ip}:${S3_PORT}:9000 ${S3_IMAGE} serve s3 --addr :9000 --auth-key ${S3_KEY},${S3_SECRET} /data
    Wait Until Keyword Succeeds    60s    3s    Run node command    curl -s -o /dev/null ${s3_endpoint}/

Install Warpgate with local recordings
    ${id} =    Install module    ${IMAGE_URL}
    Set Suite Variable    ${wg}    ${id}
    Configure    ${wg}    ${HOST}
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${wg}    ${HOST}
    ${config}    ${out} =    Configuration of    ${wg}
    Should Be Equal    ${config}[recordings][storage]    local
    Should Be Equal    ${config}[secret_backend][mode]    off
    ${storage} =    Recordings storage of    ${wg}    ${HOST}
    Should Be Equal    ${storage}[kind]    Disk
    ${args} =    Run node command    runagent -m ${wg} printenv WARPGATE_RUN_ARGS || true
    Should Be Empty    ${args}

Invalid S3 settings are refused
    Configure fails with    ${wg}    ,"recordings":{"storage":"s3","endpoint":"${s3_endpoint}","region":"us-east-1","bucket":"Bad_Bucket","access_key_id":"${S3_KEY}","secret_access_key":"${S3_SECRET}"}    s3_invalid_bucket
    Configure fails with    ${wg}    ,"recordings":{"storage":"s3","endpoint":"ftp://s3.example.org","region":"us-east-1","bucket":"${S3_BUCKET}","access_key_id":"${S3_KEY}","secret_access_key":"${S3_SECRET}"}    s3_invalid_endpoint
    Configure fails with    ${wg}    ,"recordings":{"storage":"s3","endpoint":"${s3_endpoint}","region":"us-east-1","bucket":"${S3_BUCKET}","access_key_id":"${S3_KEY}"}    required

The connection test reaches the bucket
    ${out} =    Run node command    api-cli run module/${wg}/test-recordings-storage --data '{"endpoint":"${s3_endpoint}","region":"us-east-1","bucket":"${S3_BUCKET}","path_style":true,"access_key_id":"${S3_KEY}","secret_access_key":"${S3_SECRET}"}'
    ${result} =    Evaluate    json.loads($out)    json
    Should Be True    ${result}[ok]    ${out}
    Should Not Contain    ${out}    ${S3_SECRET}
    ${out} =    Run node command    api-cli run module/${wg}/test-recordings-storage --data '{"endpoint":"${s3_endpoint}","region":"us-east-1","bucket":"${S3_BUCKET}","path_style":true,"access_key_id":"${S3_KEY}","secret_access_key":"wrong-secret"}'
    ${result} =    Evaluate    json.loads($out)    json
    Should Not Be True    ${result}[ok]

S3 storage is applied and Warpgate starts with it
    Configure    ${wg}    ${HOST}    ,"recordings":{"storage":"s3","endpoint":"${s3_endpoint}","region":"us-east-1","bucket":"${S3_BUCKET}","prefix":"robot","path_style":true,"access_key_id":"${S3_KEY}","secret_access_key":"${S3_SECRET}"}
    Run node command    runagent -m ${wg} systemctl --user is-active warpgate.service
    ${config}    ${out} =    Configuration of    ${wg}
    Should Be Equal    ${config}[recordings][storage]    s3
    Should Be True    ${config}[recordings][secret_access_key_set]
    Should Not Contain    ${out}    ${S3_SECRET}
    ${mode} =    Run node command    runagent -m ${wg} stat -c %a s3.env
    Should Be Equal    ${mode}    600
    ${rendered} =    Run node command    runagent -m ${wg} sh -c 'podman unshare cat "$(podman volume inspect --format "{{.Mountpoint}}" data)/.ns8-warpgate.yaml"'
    Should Not Contain    ${rendered}    ${S3_SECRET}
    ${env} =    Run node command    runagent -m ${wg} cat environment
    Should Not Contain    ${env}    ${S3_SECRET}
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${wg}    ${HOST}
    ${storage} =    Recordings storage of    ${wg}    ${HOST}
    Should Be Equal    ${storage}[kind]    S3
    Should Be Equal    ${storage}[bucket]    ${S3_BUCKET}
    Should Be Equal    ${storage}[prefix]    robot
    Should Be Equal    ${storage}[credentials][mode]    Auto
    ${raw} =    Evaluate    json.dumps($storage)    json
    Should Not Contain    ${raw}    ${S3_SECRET}
    # Warpgate's own round trip (put and delete an object) with the
    # credentials it got from the environment
    ${result} =    Warpgate admin API    ${wg}    ${HOST}    POST    /parameters/recordings-storage/test    ${raw}
    ${test} =    Evaluate    json.loads($result)    json
    Should Be True    ${test}[success]    ${result}

Switching back to local restores the disk storage
    Configure    ${wg}    ${HOST}    ,"recordings":{"storage":"local"}
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${wg}    ${HOST}
    ${storage} =    Recordings storage of    ${wg}    ${HOST}
    Should Be Equal    ${storage}[kind]    Disk
    Should Be Equal    ${storage}[path]    /data/recordings
    ${rc} =    Execute Command    runagent -m ${wg} test -e s3.env    return_stdout=False    return_rc=True
    Should Not Be Equal As Integers    ${rc}    0

The secret backend manual values contain no secret
    Configure    ${wg}    ${HOST}    ,"secret_backend":{"mode":"manual","name":"robot-bao"}
    ${config}    ${out} =    Configuration of    ${wg}
    ${backend} =    Set Variable    ${config}[secret_backend]
    Should Be Equal    ${backend}[mode]    manual
    Should Be Equal    ${backend}[info][backend_type]    openbao
    Should Be Equal    ${backend}[info][allowed_path]    ns8-kv/modules/${wg}/targets
    Should Start With    ${backend}[info][reference_example]    secret://robot-bao/ns8-kv/modules/${wg}/targets/
    Dictionary Should Not Contain Key    ${backend}[info]    token
    # Manual mode registers nothing in Warpgate
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${wg}    ${HOST}
    ${backends} =    Secret backends of    ${wg}    ${HOST}
    Should Be Empty    ${backends}
    Configure fails with    ${wg}    ,"secret_backend":{"mode":"managed"}    secret_backend_requires_provisioning

An upgraded instance keeps local recordings and no secret backend
    ${id} =    Install module    ${PREVIOUS_IMAGE}
    Set Suite Variable    ${old}    ${id}
    Configure    ${old}    ${UPGRADE_HOST}
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${old}    ${UPGRADE_HOST}
    Run node command    api-cli run update-module --data '{"module_url":"${IMAGE_URL}","instances":["${old}"],"force":true}'
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${old}    ${UPGRADE_HOST}
    ${config}    ${out} =    Configuration of    ${old}
    Should Be Equal    ${config}[recordings][storage]    local
    Should Be Equal    ${config}[secret_backend][mode]    off
    Should Be Empty    ${config}[recordings][warnings]
    ${storage} =    Recordings storage of    ${old}    ${UPGRADE_HOST}
    Should Be Equal    ${storage}[kind]    Disk
    Should Be Equal    ${storage}[path]    /data/recordings
    ${backends} =    Secret backends of    ${old}    ${UPGRADE_HOST}
    Should Be Empty    ${backends}
    ${args} =    Run node command    runagent -m ${old} printenv WARPGATE_RUN_ARGS || true
    Should Be Empty    ${args}
    # Saving the settings again (the UI sends every section) changes nothing
    Configure    ${old}    ${UPGRADE_HOST}    ,"recordings":{"storage":"local"},"secret_backend":{"mode":"off"}
    Wait Until Keyword Succeeds    120s    5s    Admin login works    ${old}    ${UPGRADE_HOST}
    ${storage} =    Recordings storage of    ${old}    ${UPGRADE_HOST}
    Should Be Equal    ${storage}[kind]    Disk
