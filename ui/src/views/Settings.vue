<!--
  Copyright (C) 2022 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("settings.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getConfiguration">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('action.get-configuration')"
          :description="error.getConfiguration"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <cv-form @submit.prevent="configureModule">
            <NsTextInput
              :label="$t('settings.warpgate_fqdn')"
              placeholder="warpgate.example.org"
              v-model.trim="host"
              class="mg-bottom"
              :invalid-message="error.host"
              :disabled="loading.getConfiguration || loading.configureModule"
              ref="host"
            >
            </NsTextInput>
            <NsToggle
              value="letsEncrypt"
              :label="$t('settings.lets_encrypt')"
              v-model="isLetsEncryptEnabled"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="mg-bottom"
            >
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </NsToggle>
            <NsToggle
              value="httpToHttps"
              :label="$t('settings.http_to_https')"
              v-model="isHttpToHttpsEnabled"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="mg-bottom"
            >
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </NsToggle>
            <cv-select
              v-model="oidc.mode"
              :label="$t('settings.oidc_mode')"
              :helper-text="$t('settings.oidc_mode_help')"
              :disabled="busy"
              class="mg-bottom"
            >
              <cv-select-option value="disabled">{{
                $t("settings.disabled")
              }}</cv-select-option>
              <cv-select-option value="manual">{{
                $t("settings.oidc_manual")
              }}</cv-select-option>
              <cv-select-option value="ns8">{{
                $t("settings.oidc_ns8")
              }}</cv-select-option>
            </cv-select>
            <template v-if="oidc.mode === 'manual'">
              <NsTextInput
                v-model.trim="oidc.issuer"
                :label="$t('settings.oidc_issuer')"
                :invalid-message="error.oidc_issuer"
                :disabled="busy"
                ref="oidc_issuer"
                class="mg-bottom"
              />
              <NsTextInput
                v-model.trim="oidc.client_id"
                :label="$t('settings.oidc_client_id')"
                :invalid-message="error.oidc_client_id"
                :disabled="busy"
                ref="oidc_client_id"
                class="mg-bottom"
              />
              <NsTextInput
                v-model="oidc.secret"
                type="password"
                autocomplete="new-password"
                :password-show-label="$t('settings.oidc_show_secret')"
                :password-hide-label="$t('settings.oidc_hide_secret')"
                :label="$t('settings.oidc_secret')"
                :helper-text="
                  keepsSecret ? $t('settings.oidc_keep_secret') : ''
                "
                :invalid-message="error.oidc_secret"
                :disabled="busy"
                ref="oidc_secret"
                class="mg-bottom"
              />
            </template>
            <template v-if="oidc.mode === 'ns8'">
              <cv-select
                v-model="oidc.provider"
                :label="$t('settings.oidc_provider')"
                :helper-text="
                  !oidcProviders.length ? $t('settings.oidc_no_providers') : ''
                "
                :invalid-message="error.oidc_provider"
                :disabled="busy"
                @change="oidc.domain = ''"
                ref="oidc_provider"
                class="mg-bottom"
              >
                <cv-select-option value="" disabled>{{
                  $t("settings.oidc_select_provider")
                }}</cv-select-option>
                <cv-select-option
                  v-if="oidc.provider && !selectedProvider"
                  :value="oidc.provider"
                  disabled
                  >{{
                    $t("settings.oidc_provider_unavailable")
                  }}</cv-select-option
                >
                <cv-select-option
                  v-for="provider in oidcProviders"
                  :key="provider.id"
                  :value="provider.id"
                  >{{ provider.label }}</cv-select-option
                >
              </cv-select>
              <cv-select
                v-if="oidc.provider"
                v-model="oidc.domain"
                :label="$t('settings.oidc_domain')"
                :helper-text="
                  !oidcDomains.length ? $t('settings.oidc_no_domains') : ''
                "
                :invalid-message="error.oidc_domain"
                :disabled="busy"
                ref="oidc_domain"
                class="mg-bottom"
              >
                <cv-select-option value="" disabled>{{
                  $t("settings.oidc_select_domain")
                }}</cv-select-option>
                <cv-select-option
                  v-if="oidc.domain && !oidcDomains.includes(oidc.domain)"
                  :value="oidc.domain"
                  disabled
                  >{{
                    $t("settings.oidc_domain_unavailable")
                  }}</cv-select-option
                >
                <cv-select-option
                  v-for="domain in oidcDomains"
                  :key="domain"
                  :value="domain"
                  >{{ domain }}</cv-select-option
                >
              </cv-select>
            </template>
            <NsTextInput
              v-if="oidc.mode !== 'disabled' && host && oidcCallbackPath"
              :label="$t('settings.oidc_callback')"
              :value="`https://${host}${oidcCallbackPath}`"
              readonly
              class="mg-bottom"
            />
            <cv-row v-if="error.configureModule">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="$t('action.configure-module')"
                  :description="error.configureModule"
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.configureModule"
              :disabled="loading.getConfiguration || loading.configureModule"
              >{{ $t("settings.save") }}</NsButton
            >
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
  </cv-grid>
</template>

<script>
import to from "await-to-js";
import { mapState } from "vuex";
import {
  QueryParamService,
  UtilService,
  TaskService,
  IconService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";

export default {
  name: "Settings",
  mixins: [
    TaskService,
    IconService,
    UtilService,
    QueryParamService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("settings.title") + " - " + this.appName;
  },
  data() {
    return {
      q: {
        page: "settings",
      },
      urlCheckInterval: null,
      host: "",
      isLetsEncryptEnabled: false,
      isHttpToHttpsEnabled: true,
      oidc: {
        mode: "disabled",
        issuer: "",
        client_id: "",
        secret: "",
        provider: "",
        domain: "",
      },
      savedOidc: { mode: "disabled" },
      oidcProviders: [],
      oidcCallbackPath: "",
      loading: {
        getConfiguration: false,
        configureModule: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        host: "",
        lets_encrypt: "",
        http2https: "",
        oidc_issuer: "",
        oidc_client_id: "",
        oidc_secret: "",
        oidc_provider: "",
        oidc_domain: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    busy() {
      return this.loading.getConfiguration || this.loading.configureModule;
    },
    selectedProvider() {
      return this.oidcProviders.find(({ id }) => id === this.oidc.provider);
    },
    oidcDomains() {
      return this.selectedProvider ? this.selectedProvider.domains : [];
    },
    keepsSecret() {
      return (
        this.savedOidc.mode === "manual" &&
        this.oidc.issuer === this.savedOidc.issuer &&
        this.oidc.client_id === this.savedOidc.client_id
      );
    },
  },
  created() {
    this.getConfiguration();
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.watchQueryData(vm);
      vm.urlCheckInterval = vm.initUrlBindingForApp(vm, vm.q.page);
    });
  },
  beforeRouteLeave(to, from, next) {
    clearInterval(this.urlCheckInterval);
    next();
  },
  methods: {
    async getConfiguration() {
      this.loading.getConfiguration = true;
      this.error.getConfiguration = "";
      const taskAction = "get-configuration";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.getConfigurationAborted
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.getConfigurationCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          extra: {
            title: this.$t("action." + taskAction),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`, err);
        this.error.getConfiguration = this.getErrorMessage(err);
        this.loading.getConfiguration = false;
        return;
      }
    },
    getConfigurationAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.getConfiguration = this.$t("error.generic_error");
      this.loading.getConfiguration = false;
    },
    getConfigurationCompleted(taskContext, taskResult) {
      const config = taskResult.output;
      this.host = config.host;
      this.isLetsEncryptEnabled = config.lets_encrypt;
      this.isHttpToHttpsEnabled = config.http2https;
      this.savedOidc = config.oidc || { mode: "disabled" };
      this.oidc = {
        mode: this.savedOidc.mode,
        issuer: this.savedOidc.mode === "manual" ? this.savedOidc.issuer : "",
        client_id:
          this.savedOidc.mode === "manual" ? this.savedOidc.client_id : "",
        secret: "",
        provider: this.savedOidc.provider || "",
        domain: this.savedOidc.domain || "",
      };
      this.oidcProviders = config.oidc_providers || [];
      this.oidcCallbackPath = config.oidc_callback_path || "";

      this.loading.getConfiguration = false;
      this.focusElement("host");
    },
    validateConfigureModule() {
      this.clearErrors(this);

      const required = { host: this.host };
      if (this.oidc.mode === "manual") {
        required.oidc_issuer = this.oidc.issuer;
        required.oidc_client_id = this.oidc.client_id;
        required.oidc_secret = this.oidc.secret || this.keepsSecret;
      }
      if (this.oidc.mode === "ns8") {
        required.oidc_provider = this.oidc.provider;
        required.oidc_domain = this.oidc.domain;
      }
      const missing = Object.keys(required).filter((field) => !required[field]);
      const emptyChoiceErrors = {
        oidc_provider: !this.oidcProviders.length && "settings.oidc_no_providers",
        oidc_domain:
          this.oidc.provider &&
          !this.oidcDomains.length &&
          "settings.oidc_no_domains",
      };
      missing.forEach((field) => {
        this.error[field] = this.$t(emptyChoiceErrors[field] || "common.required");
      });
      if (missing.length) {
        this.focusElement(missing[0]);
      }
      return !missing.length;
    },
    oidcPayload() {
      const { mode, provider, domain, issuer, client_id, secret } = this.oidc;
      if (mode === "ns8") return { mode, provider, domain };
      if (mode === "manual") return { mode, issuer, client_id, secret };
      return { mode };
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      let focusAlreadySet = false;

      for (const validationError of validationErrors) {
        const param = validationError.parameter;
        // set i18n error message
        this.error[param] = this.$t("settings." + validationError.error);

        if (!focusAlreadySet) {
          this.focusElement(param);
          focusAlreadySet = true;
        }
      }
    },
    async configureModule() {
      const isValidationOk = this.validateConfigureModule();
      if (!isValidationOk) {
        return;
      }

      this.loading.configureModule = true;
      const taskAction = "configure-module";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.configureModuleAborted
      );

      // register to task validation
      this.core.$root.$once(
        `${taskAction}-validation-failed-${eventId}`,
        this.configureModuleValidationFailed
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.configureModuleCompleted
      );
      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data: {
            host: this.host,
            lets_encrypt: this.isLetsEncryptEnabled,
            http2https: this.isHttpToHttpsEnabled,
            oidc: this.oidcPayload(),
          },
          extra: {
            title: this.$t("settings.instance_configuration", {
              instance: this.instanceName,
            }),
            description: this.$t("settings.configuring"),
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`);
        this.error.configureModule = this.$t("error.generic_error");
        this.loading.configureModule = false;
        return;
      }
    },
    configureModuleAborted(_taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`);
      this.error.configureModule = this.$t("error.generic_error");
      this.loading.configureModule = false;
    },
    configureModuleCompleted() {
      this.loading.configureModule = false;

      // reload configuration
      this.getConfiguration();
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
.mg-bottom {
  margin-bottom: $spacing-06;
}

.maxwidth {
  max-width: 38rem;
}
</style>
