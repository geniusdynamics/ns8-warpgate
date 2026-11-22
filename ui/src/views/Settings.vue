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
            <div class="mg-bottom">
              <h3>{{ $t("settings.database_title") }}</h3>
              <p class="mg-bottom">{{ $t("settings.database_help") }}</p>
              <cv-radio-group vertical class="mg-bottom">
                <cv-radio-button
                  v-model="dbMode"
                  value="embedded"
                  :label="$t('settings.database_embedded')"
                  :disabled="busy || savedDbMode === 'postgresql19c'"
                />
                <cv-radio-button
                  v-model="dbMode"
                  value="postgresql19c"
                  :label="$t('settings.database_postgresql')"
                  :disabled="busy || !pgInstances.length"
                />
              </cv-radio-group>
              <p v-if="!pgInstances.length" class="mg-bottom">
                {{ $t("settings.database_no_instances") }}
              </p>
              <cv-select
                v-if="dbMode === 'postgresql19c'"
                v-model="dbInstance"
                :label="$t('settings.database_instance')"
                :invalid-message="error.database"
                :disabled="busy"
                ref="database"
                class="mg-bottom"
              >
                <cv-select-option value="">{{
                  $t("settings.database_instance_auto")
                }}</cv-select-option>
                <cv-select-option
                  v-for="pg in pgInstances"
                  :key="pg.module_id"
                  :value="pg.module_id"
                  >{{
                    $t("settings.database_instance_label", {
                      id: pg.module_id,
                      node: pg.node,
                      cluster: pg.cluster_id,
                    })
                  }}</cv-select-option
                >
              </cv-select>
              <p
                v-if="savedDbMode === 'postgresql19c' && dbInfo.host"
                class="mg-bottom"
              >
                {{
                  $t("settings.database_in_use", {
                    database: dbInfo.database,
                    host: dbInfo.host,
                    port: dbInfo.port,
                  })
                }}
              </p>
            </div>
            <div class="mg-bottom">
              <h3>{{ $t("settings.cluster_title") }}</h3>
              <p class="mg-bottom">{{ $t("settings.cluster_help") }}</p>
              <cv-radio-group vertical class="mg-bottom">
                <cv-radio-button
                  v-for="mode in ['standalone', 'create', 'join']"
                  :key="mode"
                  v-model="clusterMode"
                  :value="mode"
                  :label="$t('settings.cluster_' + mode)"
                  :disabled="
                    busy ||
                    (mode !== 'standalone' && dbMode !== 'postgresql19c')
                  "
                />
              </cv-radio-group>
              <cv-select
                v-if="clusterMode === 'join'"
                v-model="clusterPeer"
                :label="$t('settings.cluster_peer')"
                :invalid-message="error.cluster"
                :disabled="busy"
                ref="cluster"
                class="mg-bottom"
              >
                <cv-select-option value="" disabled>{{
                  $t("settings.cluster_select_peer")
                }}</cv-select-option>
                <cv-select-option
                  v-for="peer in peerCandidates"
                  :key="peer.module_id"
                  :value="peer.module_id"
                  >{{ peer.ui_name || peer.module_id }}</cv-select-option
                >
              </cv-select>
              <template
                v-if="clusterMode === 'create' && peerCandidates.length"
              >
                <h4>{{ $t("settings.peer_approvals") }}</h4>
                <p class="mg-bottom">
                  {{ $t("settings.peer_approvals_help") }}
                </p>
                <cv-data-table
                  :columns="[
                    $t('settings.peer_instance'),
                    $t('settings.peer_node'),
                    $t('settings.peer_allowed'),
                  ]"
                  class="mg-bottom"
                >
                  <template slot="data">
                    <cv-data-table-row
                      v-for="peer in peerCandidates"
                      :key="peer.module_id"
                    >
                      <cv-data-table-cell>{{
                        peer.ui_name
                          ? `${peer.ui_name} (${peer.module_id})`
                          : peer.module_id
                      }}</cv-data-table-cell>
                      <cv-data-table-cell>{{ peer.node }}</cv-data-table-cell>
                      <cv-data-table-cell>
                        <NsToggle
                          :value="'peer-' + peer.module_id"
                          :form-item="false"
                          hideLabel
                          :label="$t('settings.peer_allowed')"
                          :checked="peer.allowed"
                          :disabled="busy || loading.peer === peer.module_id"
                          @change="setPeerAccess(peer, $event)"
                        >
                          <template slot="text-left">{{
                            $t("settings.disabled")
                          }}</template>
                          <template slot="text-right">{{
                            $t("settings.enabled")
                          }}</template>
                        </NsToggle>
                      </cv-data-table-cell>
                    </cv-data-table-row>
                  </template>
                </cv-data-table>
              </template>
              <NsInlineNotification
                v-if="error.peer"
                kind="error"
                :description="error.peer"
                :showCloseButton="false"
                class="mg-bottom"
              />
            </div>
            <div class="mg-bottom">
              <h3>{{ $t("settings.vault_title") }}</h3>
              <p class="mg-bottom">{{ $t("settings.vault_help") }}</p>
              <NsToggle
                value="vaultEnabled"
                :label="$t('settings.vault_enabled')"
                v-model="vaultEnabled"
                :disabled="busy"
                class="mg-bottom"
              >
                <template slot="text-left">{{
                  $t("settings.disabled")
                }}</template>
                <template slot="text-right">{{
                  $t("settings.enabled")
                }}</template>
              </NsToggle>
              <template v-if="vaultEnabled">
                <cv-radio-group vertical class="mg-bottom">
                  <cv-radio-button
                    v-model="vaultMode"
                    value="provisioned"
                    :label="$t('settings.vault_provisioned')"
                    :disabled="busy || !openbaoServers.length"
                  />
                  <cv-radio-button
                    v-model="vaultMode"
                    value="manual"
                    :label="$t('settings.vault_manual')"
                    :disabled="busy"
                  />
                </cv-radio-group>
                <template v-if="vaultMode === 'provisioned'">
                  <cv-select
                    v-model="vaultOpenbao"
                    :label="$t('settings.vault_openbao')"
                    :invalid-message="error.vault_openbao"
                    :disabled="busy"
                    ref="vault_openbao"
                    class="mg-bottom"
                  >
                    <cv-select-option value="" disabled>{{
                      $t("settings.vault_select_openbao")
                    }}</cv-select-option>
                    <cv-select-option
                      v-for="bao in openbaoServers"
                      :key="bao.module_id"
                      :value="bao.module_id"
                      >{{ bao.ui_name || bao.module_id }}</cv-select-option
                    >
                  </cv-select>
                  <p v-if="openbaoStatus.status" class="mg-bottom">
                    {{ $t("settings.vault_status_" + openbaoStatus.status) }}
                  </p>
                  <NsButton
                    type="button"
                    kind="secondary"
                    size="small"
                    class="mg-bottom"
                    :loading="loading.requestAccess"
                    :disabled="busy || !vaultOpenbao || loading.requestAccess"
                    @click="requestOpenbaoAccess"
                    >{{ $t("settings.vault_request_access") }}</NsButton
                  >
                </template>
                <template v-else>
                  <NsTextInput
                    v-model.trim="vaultAddress"
                    :label="$t('settings.vault_address')"
                    placeholder="https://openbao.example.org"
                    :invalid-message="error.vault_address"
                    :disabled="busy"
                    ref="vault_address"
                    class="mg-bottom"
                  />
                  <NsTextInput
                    v-model="vaultToken"
                    type="password"
                    autocomplete="new-password"
                    :password-show-label="$t('settings.oidc_show_secret')"
                    :password-hide-label="$t('settings.oidc_hide_secret')"
                    :label="$t('settings.vault_token')"
                    :helper-text="
                      vaultTokenSet ? $t('settings.vault_token_keep') : ''
                    "
                    :invalid-message="error.vault_token"
                    :disabled="busy"
                    ref="vault_token"
                    class="mg-bottom"
                  />
                </template>
              </template>
              <NsInlineNotification
                v-if="error.requestAccess"
                kind="error"
                :description="error.requestAccess"
                :showCloseButton="false"
                class="mg-bottom"
              />
            </div>
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
      dbMode: "embedded",
      savedDbMode: "embedded",
      dbInstance: "",
      dbInfo: {},
      pgInstances: [],
      clusterMode: "standalone",
      clusterPeer: "",
      peerCandidates: [],
      vaultEnabled: false,
      vaultMode: "provisioned",
      vaultOpenbao: "",
      vaultAddress: "",
      vaultToken: "",
      vaultTokenSet: false,
      openbaoServers: [],
      openbaoStatus: {},
      loading: {
        getConfiguration: false,
        configureModule: false,
        peer: "",
        requestAccess: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        host: "",
        lets_encrypt: "",
        http2https: "",
        oidc_entries: "",
        database: "",
        cluster: "",
        peer: "",
        requestAccess: "",
        vault_openbao: "",
        vault_address: "",
        vault_token: "",
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
      const db = config.database || {};
      this.dbMode = this.savedDbMode = db.mode || "embedded";
      this.dbInstance = db.instance || "";
      this.dbInfo = db;
      this.pgInstances = config.postgresql19c_instances || [];
      const cluster = config.cluster || {};
      this.clusterMode = cluster.mode || "standalone";
      this.clusterPeer = cluster.peer || "";
      this.peerCandidates = config.peer_candidates || [];
      this.vaultEnabled = Boolean(config.vault_enabled);
      this.vaultMode = config.vault_mode || "provisioned";
      this.vaultOpenbao = config.vault_openbao || "";
      this.vaultAddress = config.vault_address || "";
      this.vaultToken = "";
      this.vaultTokenSet = Boolean(config.vault_token_set);
      this.openbaoServers = config.openbao_servers || [];
      this.openbaoStatus = config.openbao_client_status || {};

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
      if (this.clusterMode === "join" && !this.clusterPeer) {
        this.error.cluster = this.$t("common.required");
      }
      if (this.vaultEnabled && this.vaultMode === "provisioned") {
        if (!this.vaultOpenbao)
          this.error.vault_openbao = this.$t("common.required");
      } else if (this.vaultEnabled) {
        if (!this.vaultAddress)
          this.error.vault_address = this.$t("common.required");
        if (!this.vaultToken && !this.vaultTokenSet)
          this.error.vault_token = this.$t("common.required");
      }
      const otherError = [
        "cluster",
        "vault_openbao",
        "vault_address",
        "vault_token",
      ].find((field) => this.error[field]);
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
      } else if (otherError) this.focusElement(otherError);
      return !this.error.host && !firstInvalidEntry && !otherError;
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
        let param = validationError.parameter.startsWith("oidc")
          ? "oidc_entries"
          : validationError.parameter;
        if (param.startsWith("database")) param = "database";
        if (param.startsWith("cluster")) param = "cluster";
        if (!(param in this.error)) param = "configureModule";
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
            database: { mode: this.dbMode, instance: this.dbInstance },
            cluster: {
              mode: this.clusterMode,
              peer: this.clusterMode === "join" ? this.clusterPeer : "",
            },
            ...this.vaultPayload(),
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
    vaultPayload() {
      if (!this.vaultEnabled) return { vault_enabled: false };
      if (this.vaultMode === "provisioned") {
        return {
          vault_enabled: true,
          vault_mode: "provisioned",
          vault_openbao: this.vaultOpenbao,
        };
      }
      return {
        vault_enabled: true,
        vault_mode: "manual",
        vault_address: this.vaultAddress,
        ...(this.vaultToken ? { vault_token: this.vaultToken } : {}),
      };
    },
    async runAction(action, data, onCompleted, onFailed) {
      const eventId = this.getUuid();
      this.core.$root.$once(`${action}-aborted-${eventId}`, onFailed);
      this.core.$root.$once(`${action}-validation-failed-${eventId}`, onFailed);
      this.core.$root.$once(`${action}-completed-${eventId}`, onCompleted);
      const [err] = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action,
          data,
          extra: {
            title: this.$t("action." + action),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      if (err) onFailed();
    },
    setPeerAccess(peer, allowed) {
      this.error.peer = "";
      this.loading.peer = peer.module_id;
      this.runAction(
        "set-peer-access",
        { peer: peer.module_id, allowed: Boolean(allowed) },
        () => {
          peer.allowed = Boolean(allowed);
          this.loading.peer = "";
        },
        () => {
          this.error.peer = this.$t("error.generic_error");
          this.loading.peer = "";
        }
      );
    },
    requestOpenbaoAccess() {
      this.error.requestAccess = "";
      this.loading.requestAccess = true;
      this.runAction(
        "request-openbao-access",
        { openbao: this.vaultOpenbao },
        (_taskContext, taskResult) => {
          this.openbaoStatus = taskResult.output || {};
          this.loading.requestAccess = false;
        },
        () => {
          this.error.requestAccess = this.$t("settings.openbao_request_failed");
          this.loading.requestAccess = false;
        }
      );
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
