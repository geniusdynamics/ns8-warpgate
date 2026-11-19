*** Settings ***
Library    SSHLibrary
Library    Collections

*** Variables ***
${ADMIN_USER}    admin
${ADMIN_PASSWORD}    Nethesis,1234
${module_id}    ${EMPTY}
${HOST}    warpgate.example.org
${OIDC_DOMAIN}    warpgate-sso.example.org
${KEYCLOAK_HOST}    keycloak.${OIDC_DOMAIN}
${DIRECTORY_IMAGE}    ghcr.io/nethserver/openldap:2.8.1
${KEYCLOAK_IMAGE}    ghcr.io/geniusdynamics/keycloak:1.1.0
${directory_id}    ${EMPTY}
${keycloak_id}    ${EMPTY}

*** Keywords ***
Login to cluster-admin
    New Page    https://${NODE_ADDR}/cluster-admin/
    Fill Text    text="Username"    ${ADMIN_USER}
    Click    button >> text="Continue"
    Fill Text    text="Password"    ${ADMIN_PASSWORD}
    Click    button >> text="Log in"
    Wait For Elements State    css=#main-content    visible    timeout=10s

Warpgate answers through Traefik
    ${rc} =    Execute Command
    ...    curl -k -f -L --resolve ${HOST}:443:127.0.0.1 --resolve ${HOST}:80:127.0.0.1 http://${HOST}/@warpgate/
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Configure OIDC
    [Arguments]    ${oidc}
    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"host":"${HOST}","http2https":true,"lets_encrypt":false,"oidc":${oidc}}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}    0

Configure OIDC entries
    [Arguments]    ${entries}
    Run node command    api-cli run module/${module_id}/configure-module --data '{"host":"${HOST}","http2https":true,"lets_encrypt":false,"oidc_entries":${entries}}'

OIDC provider count should be
    [Arguments]    ${expected}
    Wait Until Keyword Succeeds    60s    3s    Check OIDC provider count    ${expected}

Check OIDC provider count
    [Arguments]    ${expected}
    ${output}    ${rc} =    Execute Command
    ...    curl -kf --resolve ${HOST}:443:127.0.0.1 https://${HOST}/@warpgate/api/sso/providers
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}    0
    ${count} =    Evaluate    len(json.loads($output))    json
    Should Be Equal As Integers    ${count}    ${expected}

Run node command
    [Arguments]    ${command}
    ${out}    ${err}    ${rc} =    Execute Command    ${command}    return_stderr=True    return_rc=True
    Should Be Equal As Integers    ${rc}    0    ${out} ${err}
    RETURN    ${out}

Install OIDC fixture
    [Arguments]    ${image}
    ${out} =    Run node command    add-module ${image} 1
    ${id} =    Evaluate    ast.literal_eval($out)['module_id']    ast
    RETURN    ${id}

Remove OIDC fixtures
    FOR    ${id}    IN    ${keycloak_id}    ${directory_id}
        IF    $id
            Run node command    remove-module --no-preserve ${id}
        END
    END

*** Test Cases ***
Check if warpgate is installed correctly
    ${output}  ${rc} =    Execute Command    add-module ${IMAGE_URL} 1
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{output} =    Evaluate    ${output}
    Set Global Variable    ${module_id}    ${output.module_id}

Check if warpgate can be configured
    ${rc} =    Execute Command    api-cli run module/${module_id}/configure-module --data '{"host":"${HOST}","http2https":true,"lets_encrypt":false}'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Check if the configuration is returned
    ${output}  ${rc} =    Execute Command    api-cli run module/${module_id}/get-configuration
    ...    return_rc=True
    Should Be Equal As Integers    ${rc}  0
    &{config} =    Evaluate    json.loads($output)    json
    Should Be Equal    ${config.host}    ${HOST}

Check if OIDC is disabled by default
    ${output} =    Execute Command    api-cli run module/${module_id}/get-configuration
    &{config} =    Evaluate    json.loads($output)    json
    Should Be Equal    ${config.oidc.mode}    disabled
    OIDC provider count should be    0

Check if external OIDC can be enabled, retained, and disabled
    Configure OIDC    {"mode":"manual","issuer":"https://identity.example.org/realm","client_id":"warpgate-test","secret":"test-client-secret"}
    OIDC provider count should be    1
    Configure OIDC    {"mode":"manual","issuer":"https://identity.example.org/realm","client_id":"warpgate-test"}
    OIDC provider count should be    1
    ${output} =    Execute Command    api-cli run module/${module_id}/get-configuration
    &{config} =    Evaluate    json.loads($output)    json
    Should Be Equal    ${config.oidc.issuer}    https://identity.example.org/realm
    Dictionary Should Not Contain Key    ${config.oidc}    secret
    Configure OIDC    {"mode":"disabled"}
    OIDC provider count should be    0

Check if a published NS8 provider can be selected and registered
    [Teardown]    Remove OIDC fixtures
    ${directory} =    Install OIDC fixture    ${DIRECTORY_IMAGE}
    Set Suite Variable    ${directory_id}    ${directory}
    Run node command    api-cli run module/${directory_id}/configure-module --data '{"provision":"new-domain","domain":"${OIDC_DOMAIN}","admuser":"admin","admpass":"OIDC-CI-password-2026"}'
    ${keycloak} =    Install OIDC fixture    ${KEYCLOAK_IMAGE}
    Set Suite Variable    ${keycloak_id}    ${keycloak}
    Run node command    api-cli run module/${keycloak_id}/configure-module --data '{"host":"${KEYCLOAK_HOST}","http2https":true,"lets_encrypt":false}'
    Wait Until Keyword Succeeds    150s    5s    Run node command
    ...    curl -kfSs --resolve ${KEYCLOAK_HOST}:443:127.0.0.1 https://${KEYCLOAK_HOST}/realms/master/.well-known/openid-configuration >/dev/null
    Run node command    api-cli run module/${keycloak_id}/configure-ns8-sso --data '{"enabled":true}'
    ${provider} =    Run node command    redis-cli --no-auth-warning hget cluster/module_uuid ${keycloak_id}
    ${output} =    Run node command    api-cli run module/${module_id}/get-configuration
    ${domains} =    Evaluate    {x['id']: x['domains'] for x in json.loads($output)['oidc_providers']}[$provider]    json
    Should Contain    ${domains}    ${OIDC_DOMAIN}
    Configure OIDC    {"mode":"ns8","provider":"${provider}","domain":"${OIDC_DOMAIN}"}
    OIDC provider count should be    1
    ${output} =    Run node command    api-cli run module/${module_id}/get-configuration
    &{config} =    Evaluate    json.loads($output)    json
    Should Be Equal    ${config.oidc.mode}    ns8
    Should Be Equal    ${config.oidc.issuer}    https://${KEYCLOAK_HOST}/realms/${OIDC_DOMAIN}
    Should Be Equal    ${config.oidc.client_id}    ${module_id}
    Dictionary Should Not Contain Key    ${config.oidc}    secret
    ${before} =    Run node command    runagent -m ${module_id} sha256sum oidc.json
    Run node command    runagent -m ${module_id} refresh-warpgate-oidc
    ${same} =    Run node command    runagent -m ${module_id} sha256sum oidc.json
    Should Be Equal    ${same}    ${before}
    Run node command    runagent -m ${module_id} refresh-warpgate-oidc --rotate-secret
    ${after} =    Run node command    runagent -m ${module_id} sha256sum oidc.json
    Should Not Be Equal    ${after}    ${before}
    OIDC provider count should be    1
    Configure OIDC entries
    ...    [{"mode":"ns8","provider":"${provider}","domain":"${OIDC_DOMAIN}"},{"mode":"manual","label":"Provider A","issuer":"https://a.example.org/realm","client_id":"client-a","secret":"secret-a"},{"mode":"manual","label":"Provider B","issuer":"https://b.example.org/realm","client_id":"client-b","secret":"secret-b"}]
    OIDC provider count should be    3
    ${output} =    Run node command    api-cli run module/${module_id}/get-configuration
    &{config} =    Evaluate    json.loads($output)    json
    Length Should Be    ${config.oidc_entries}    3
    FOR    ${entry}    IN    @{config.oidc_entries}
        Dictionary Should Not Contain Key    ${entry}    secret
    END
    Configure OIDC entries
    ...    [{"mode":"ns8","provider":"${provider}","domain":"${OIDC_DOMAIN}"},{"mode":"manual","label":"Provider B","issuer":"https://b.example.org/realm","client_id":"client-b"}]
    OIDC provider count should be    2
    Configure OIDC entries    []
    OIDC provider count should be    0

Check if warpgate works as expected
    Wait Until Keyword Succeeds    60s    3s    Warpgate answers through Traefik

Check if the SSH and MySQL listeners are published
    ${rc} =    Execute Command    runagent -m ${module_id} sh -c 'ss -ltn | grep -q ":$TCP_PORT_SSH " && ss -ltn | grep -q ":$TCP_PORT_MYSQL "'
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0

Take screenshots
    [Tags]    ui
    Import Library    Browser
    New Browser    chromium    headless=True
    New Context    ignoreHTTPSErrors=True
    Login to cluster-admin
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}
    Wait For Elements State    iframe >>> h2 >> text="Status"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/1._Status.png
    Go To    https://${NODE_ADDR}/cluster-admin/#/apps/${module_id}?page=settings
    Wait For Elements State    iframe >>> h2 >> text="Settings"    visible    timeout=10s
    Sleep    5s
    Take Screenshot    filename=${OUTPUT DIR}/browser/screenshot/2._Settings.png
    Close Browser

Check if warpgate is removed correctly
    ${rc} =    Execute Command    remove-module --no-preserve ${module_id}
    ...    return_rc=True  return_stdout=False
    Should Be Equal As Integers    ${rc}  0
