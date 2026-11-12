<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-tile kind="standard" :light="light" class="ns-backup-card ns-card">
    <!-- icon -->
    <div class="row">
      <NsSvg :svg="Save32" />
    </div>
    <div class="row">
      <h3 class="title">{{ title }}</h3>
    </div>
    <div v-if="loading" class="row">
      <cv-skeleton-text
        :paragraph="true"
        :line-count="2"
        class="loading-skeleton"
      ></cv-skeleton-text>
    </div>
    <template v-else-if="!backupsContainingInstance.length">
      <div class="row no-backup">
        <!-- no backup -->
        <NsSvg :svg="Warning16" class="icon status-warning" />
        <span>
          {{ noBackupMessage }}
        </span>
      </div>
    </template>
    <template v-else>
      <div class="backups">
        <div v-if="backupsContainingInstance.length == 1" class="backup">
          <div class="table-wrapper">
            <div class="table">
              <!-- status -->
              <div class="tr">
                <div class="td label">{{ statusLabel }}</div>
                <div class="td status">
                  <span v-if="!singleBackup.enabled" class="status-warning">
                    {{ backupDisabledLabel }}
                  </span>
                  <span
                    v-else-if="
                      status[singleBackup.id] &&
                      status[singleBackup.id].success == true
                    "
                    class="status-success"
                  >
                    <span>{{ statusSuccessLabel }}</span>
                  </span>
                  <span
                    v-else-if="
                      status[singleBackup.id] &&
                      status[singleBackup.id].success == false
                    "
                    class="status-error"
                  >
                    {{ statusErrorLabel }}
                  </span>
                  <span v-else class="status-warning">
                    {{ statusNotRunLabel }}
                  </span>
                </div>
              </div>
              <NsBackupCardDetails
                :backup="singleBackup"
                :status="status"
                :repositoryLabel="repositoryLabel"
                :completedLabel="completedLabel"
                :durationLabel="durationLabel"
                :totalSizeLabel="totalSizeLabel"
                :totalFileCountLabel="totalFileCountLabel"
              />
            </div>
          </div>
        </div>
        <div v-else>
          <!-- multiple backups for this instance -->
          <div class="table-wrapper">
            <div class="table">
              <!-- status -->
              <div class="tr">
                <div class="td label">{{ statusLabel }}</div>
                <div class="td status">
                  <span
                    v-if="summaryStatus && summaryStatus.success == true"
                    class="status-success"
                  >
                    <span>{{ statusSuccessLabel }}</span>
                  </span>
                  <span
                    v-else-if="summaryStatus && summaryStatus.success == false"
                    class="status-error"
                  >
                    {{ statusErrorLabel }}
                  </span>
                  <span v-else class="status-warning">
                    {{ multipleUncertainStatusLabel }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
    <div>
      <div class="row footer">
        <NsButton
          kind="ghost"
          :icon="ArrowRight20"
          @click="goToBackup"
          :disabled="loading"
          >{{ goToBackupLabel }}
        </NsButton>
      </div>
    </div>
  </cv-tile>
</template>

<script>
import IconService from "../lib-mixins/icon.js";
import UtilService from "../lib-mixins/util.js";
import NsBackupCardDetails from "./NsBackupCardDetails";
export default {
  name: "NsBackupCard",
  components: { NsBackupCardDetails },
  mixins: [IconService, UtilService],
  props: {
    title: {
      type: String,
      default: "Backup",
    },
    noBackupMessage: {
      type: String,
      default: "No backup configured",
    },
    goToBackupLabel: {
      type: String,
      default: "Go to Backup",
    },
    repositoryLabel: {
      type: String,
      default: "Repository",
    },
    statusLabel: {
      type: String,
      default: "Status",
    },
    statusSuccessLabel: {
      type: String,
      default: "Success",
    },
    statusNotRunLabel: {
      type: String,
      default: "Backup has not run yet",
    },
    statusErrorLabel: {
      type: String,
      default: "Error",
    },
    completedLabel: {
      type: String,
      default: "Completed",
    },
    durationLabel: {
      type: String,
      default: "Duration",
    },
    totalSizeLabel: {
      type: String,
      default: "Total size",
    },
    totalFileCountLabel: {
      type: String,
      default: "Total file count",
    },
    backupDisabledLabel: {
      type: String,
      default: "Disabled",
    },
    showMoreLabel: {
      type: String,
      default: "Show more",
    },
    multipleUncertainStatusLabel: {
      type: String,
      default: "Some backups failed or are pending",
    },
    moduleId: {
      type: String,
      required: true,
    },
    moduleUiName: {
      type: String,
      default: "",
    },
    repositories: {
      type: Array,
      required: true,
    },
    backups: {
      type: Array,
      required: true,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    coreContext: {
      type: Object,
      required: true,
    },
    light: Boolean,
  },
  data() {
    return {
      backupsContainingInstance: [],
      status: {},
      summaryStatus: undefined,
    };
  },
  computed: {
    singleBackup() {
      return this.backupsContainingInstance.length === 1
        ? this.backupsContainingInstance[0]
        : null;
    },
  },
  watch: {
    repositories: function () {
      this.updateData();
    },
    backups: function () {
      this.updateData();
    },
  },
  created() {
    this.updateData();
  },
  methods: {
    updateData() {
      let backupsContainingInstance = [];

      for (const backup of this.backups) {
        for (const instance of backup.instances) {
          if (instance.module_id == this.moduleId) {
            backupsContainingInstance.push(backup);
          }
        }
      }
      this.backupsContainingInstance = backupsContainingInstance;

      // status
      for (const backup of this.backupsContainingInstance) {
        const instance = backup.instances.find(
          (i) => i.module_id == this.moduleId
        );
        const instanceStatus = instance.status;
        this.status[backup.id] = instanceStatus;

        // overwrite summary status if:
        // - it is undefined (first time loading)
        // - the status is not successful
        // - the status is null (not run yet) and the previous status was true (successful)
        if (
          this.summaryStatus === undefined ||
          (instanceStatus && instanceStatus.success === false) ||
          (instanceStatus &&
            instanceStatus.success === null &&
            this.summaryStatus === true)
        ) {
          this.summaryStatus = instanceStatus;
        }
      }
    },
    goToBackup() {
      if (this.coreContext && this.coreContext.$router) {
        this.coreContext.$router.push("/backup");
      }
    },
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tokens";

.ns-backup-card {
  display: flex;
  flex-direction: column;
  min-height: 7rem;
}

.backup {
  margin-bottom: 1rem;
}

.backup:last-child {
  margin-bottom: 0;
}

.row {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.5rem;
}

.title {
  margin-left: 0.25rem;
  margin-right: 0.25rem;
  margin-bottom: 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.table-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 0.5rem;
  margin-bottom: 0.5rem;
}

.table {
  display: table;
}

.tr {
  display: table-row;
}

.td {
  display: table-cell;
}

.label {
  padding-right: 0.75rem;
  font-weight: bold;
  text-align: right;
  padding-bottom: 0.5rem;
}

.status {
  font-weight: bold;
}

.backup-status-icon {
  margin-right: 0.25rem;
}

.loading-skeleton,
.footer {
  margin-top: $spacing-03;
}

.no-backup .icon {
  margin-right: $spacing-03;
}

.status-success {
  color: $support-02;
  fill: $support-02;
}

.status-error {
  color: $danger-01;
  fill: $danger-01;
}

.status-warning {
  color: $ns-warning-color;
  fill: $ns-warning-color;
}
</style>

<style lang="scss">
// global styles

.ns-backup-card .bx--accordion--start .bx--accordion__content {
  margin-left: 0;
}
</style>
