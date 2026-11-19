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
            <div class="mg-bottom">
              <h3>{{ $t("settings.oidc_mode") }}</h3>
              <p class="mg-bottom">{{ $t("settings.oidc_mode_help") }}</p>
              <NsInlineNotification
                v-if="error.oidc_entries"
                ref="oidc_entries"
                tabindex="-1"
                kind="error"
                :description="error.oidc_entries"
                :showCloseButton="false"
                class="mg-bottom"
              />
              <h4>{{ $t("settings.oidc_ns8") }}</h4>
              <p v-if="!oidcProviders.length" class="mg-bottom">
                {{ $t("settings.oidc_no_providers") }}
              </p>
              <div
                v-for="entry in ns8Entries"
                :key="entry.rowId"
                :ref="'entry-' + entry.rowId"
                class="mg-bottom"
              >
                <cv-select
                  v-model="entry.provider"
                  :label="$t('settings.oidc_provider')"
                  :invalid-message="entry.errors.provider"
                  :aria-invalid="Boolean(entry.errors.provider)"
                  :disabled="busy"
                  @change="entry.domain = ''"
                  class="mg-bottom"
                >
                  <cv-select-option value="" disabled>{{
                    $t("settings.oidc_select_provider")
                  }}</cv-select-option>
                  <cv-select-option
                    v-if="entry.provider && !selectedProvider(entry)"
                    :value="entry.provider"
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
                  v-if="entry.provider"
                  v-model="entry.domain"
                  :label="$t('settings.oidc_domain')"
                  :helper-text="
                    !oidcDomains(entry).length
                      ? $t('settings.oidc_no_domains')
                      : ''
                  "
                  :invalid-message="entry.errors.domain"
                  :aria-invalid="Boolean(entry.errors.domain)"
                  :disabled="busy"
                  class="mg-bottom"
                >
                  <cv-select-option value="" disabled>{{
                    $t("settings.oidc_select_domain")
                  }}</cv-select-option>
                  <cv-select-option
                    v-if="
                      entry.domain && !oidcDomains(entry).includes(entry.domain)
                    "
                    :value="entry.domain"
                    disabled
                    >{{
                      $t("settings.oidc_domain_unavailable")
                    }}</cv-select-option
                  >
                  <cv-select-option
                    v-for="domain in oidcDomains(entry)"
                    :key="domain"
                    :value="domain"
                    >{{ domain }}</cv-select-option
                  >
                </cv-select>
                <NsButton
                  type="button"
                  kind="danger--ghost"
                  size="small"
                  :disabled="busy"
                  @click="removeOidcEntry(entry)"
                  >{{ $t("settings.oidc_remove") }}</NsButton
                >
              </div>
              <NsButton
                type="button"
                kind="secondary"
                size="small"
                :disabled="busy || !oidcProviders.length"
                ref="add-ns8"
                @click="addOidcEntry('ns8')"
                >{{ $t("settings.oidc_add_ns8") }}</NsButton
              >
            </div>
            <cv-accordion
              class="mg-bottom"
              @cv:change="manualExpanded = $event.dataOpen"
            >
              <cv-accordion-item :open="manualExpanded">
                <template slot="title">{{ $t("settings.advanced") }}</template>
                <template slot="content">
                  <h4>{{ $t("settings.oidc_manual") }}</h4>
                  <div
                    v-for="entry in manualEntries"
                    :key="entry.rowId"
                    :ref="'entry-' + entry.rowId"
                    class="mg-bottom"
                  >
                    <NsTextInput
                      v-model.trim="entry.label"
                      maxlength="120"
                      :label="$t('settings.oidc_label')"
                      :disabled="busy"
                      class="mg-bottom"
                    />
                    <NsTextInput
                      v-model.trim="entry.issuer"
                      :label="$t('settings.oidc_issuer')"
                      :invalid-message="entry.errors.issuer"
                      :aria-invalid="Boolean(entry.errors.issuer)"
                      :disabled="busy"
                      class="mg-bottom"
                    />
                    <NsTextInput
                      v-model.trim="entry.client_id"
                      :label="$t('settings.oidc_client_id')"
                      :invalid-message="entry.errors.client_id"
                      :aria-invalid="Boolean(entry.errors.client_id)"
                      :disabled="busy"
                      class="mg-bottom"
                    />
                    <NsTextInput
                      v-model="entry.secret"
                      type="password"
                      autocomplete="new-password"
                      :password-show-label="$t('settings.oidc_show_secret')"
                      :password-hide-label="$t('settings.oidc_hide_secret')"
                      :label="$t('settings.oidc_secret')"
                      :helper-text="
                        keepsSecret(entry)
                          ? $t('settings.oidc_keep_secret')
                          : ''
                      "
                      :invalid-message="entry.errors.secret"
                      :aria-invalid="Boolean(entry.errors.secret)"
                      :disabled="busy"
                      class="mg-bottom"
                    />
                    <NsButton
                      type="button"
                      kind="danger--ghost"
                      size="small"
                      :disabled="busy"
                      @click="removeOidcEntry(entry)"
                      >{{ $t("settings.oidc_remove") }}</NsButton
                    >
                  </div>
                  <NsButton
                    type="button"
                    kind="secondary"
                    size="small"
                    :disabled="busy"
                    ref="add-manual"
                    @click="addOidcEntry('manual')"
                    >{{ $t("settings.oidc_add_manual") }}</NsButton
                  >
                </template>
              </cv-accordion-item>
            </cv-accordion>
            <NsTextInput
              v-if="oidcEntries.length && host && oidcCallbackPath"
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
              ref="saveSettings"
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
      oidcEntries: [],
      savedOidcEntries: [],
      manualExpanded: false,
      nextOidcRowId: 0,
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
        oidc_entries: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    busy() {
      return this.loading.getConfiguration || this.loading.configureModule;
    },
    ns8Entries() {
      return this.oidcEntries.filter(({ mode }) => mode === "ns8");
    },
    manualEntries() {
      return this.oidcEntries.filter(({ mode }) => mode === "manual");
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
      const legacy = config.oidc;
      this.savedOidcEntries =
        config.oidc_entries ||
        (legacy && legacy.mode !== "disabled" ? [legacy] : []);
      this.oidcEntries = this.savedOidcEntries.map((entry) =>
        this.createOidcEntry(entry.mode, entry)
      );
      this.oidcProviders = config.oidc_providers || [];
      this.oidcCallbackPath = config.oidc_callback_path || "";

      this.loading.getConfiguration = false;
      this.focusElement("host");
    },
    selectedProvider(entry) {
      return this.oidcProviders.find(({ id }) => id === entry.provider);
    },
    oidcDomains(entry) {
      const provider = this.selectedProvider(entry);
      return provider ? provider.domains : [];
    },
    keepsSecret(entry) {
      return this.savedOidcEntries.some(
        ({ mode, issuer, client_id }) =>
          mode === "manual" &&
          issuer === entry.issuer &&
          client_id === entry.client_id
      );
    },
    createOidcEntry(mode, entry = {}) {
      return {
        rowId: this.nextOidcRowId++,
        mode,
        issuer: entry.issuer || "",
        client_id: entry.client_id || "",
        label: entry.label || "",
        secret: "",
        provider: entry.provider || "",
        domain: entry.domain || "",
        errors: {},
      };
    },
    focusOidcEntry(entry, invalidOnly = false) {
      this.$nextTick(() => {
        const rows = this.$refs["entry-" + entry.rowId];
        if (!rows || !rows.length) return;
        const selector = invalidOnly
          ? '[aria-invalid="true"], [data-invalid] input, [data-invalid] select'
          : "input, select";
        const field = rows[0].querySelector(selector);
        if (field) field.focus();
      });
    },
    addOidcEntry(mode) {
      const entry = this.createOidcEntry(mode);
      this.oidcEntries.push(entry);
      this.focusOidcEntry(entry);
    },
    removeOidcEntry(entry) {
      this.oidcEntries = this.oidcEntries.filter(
        ({ rowId }) => rowId !== entry.rowId
      );
      this.$nextTick(() => {
        const addButton = this.$refs["add-" + entry.mode].$el;
        const target = addButton.disabled
          ? this.$refs.saveSettings.$el
          : addButton;
        target.focus();
      });
    },
    validateConfigureModule() {
      this.clearErrors(this);

      if (!this.host) this.error.host = this.$t("common.required");
      let firstInvalidEntry;
      for (const entry of [...this.ns8Entries, ...this.manualEntries]) {
        const required =
          entry.mode === "ns8"
            ? { provider: entry.provider, domain: entry.domain }
            : {
                issuer: entry.issuer,
                client_id: entry.client_id,
                secret: entry.secret || this.keepsSecret(entry),
              };
        const errors = {};
        for (const field of Object.keys(required)) {
          if (!required[field]) errors[field] = this.$t("common.required");
        }
        if (
          entry.provider &&
          !entry.domain &&
          !this.oidcDomains(entry).length
        ) {
          errors.domain = this.$t("settings.oidc_no_domains");
        }
        entry.errors = errors;
        if (!firstInvalidEntry && Object.keys(errors).length) {
          firstInvalidEntry = entry;
        }
      }
      if (this.error.host) this.focusElement("host");
      else if (firstInvalidEntry) {
        if (firstInvalidEntry.mode === "manual") this.manualExpanded = true;
        this.focusOidcEntry(firstInvalidEntry, true);
      }
      return !this.error.host && !firstInvalidEntry;
    },
    oidcPayload() {
      return this.oidcEntries.map((entry) => {
        const { mode, provider, domain, issuer, client_id, label, secret } =
          entry;
        if (mode === "ns8") return { mode, provider, domain };
        return { mode, issuer, client_id, ...(label ? { label } : {}), secret };
      });
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      let focusAlreadySet = false;

      for (const validationError of validationErrors) {
        const param = validationError.parameter.startsWith("oidc")
          ? "oidc_entries"
          : validationError.parameter;
        // set i18n error message
        this.error[param] = this.$t("settings." + validationError.error);

        if (!focusAlreadySet) {
          if (param === "oidc_entries") {
            this.$nextTick(() => {
              const notification = this.$refs.oidc_entries;
              if (notification) notification.$el.focus();
            });
          } else this.focusElement(param);
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
            oidc_entries: this.oidcPayload(),
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
