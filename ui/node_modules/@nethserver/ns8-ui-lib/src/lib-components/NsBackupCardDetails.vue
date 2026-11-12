<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div class="ns-backup-card-details">
    <!-- repository -->
    <div class="tr">
      <div class="td label">{{ repositoryLabel }}</div>
      <div class="td">
        {{ backup.repoName }}
      </div>
    </div>
    <!-- completed -->
    <div class="tr">
      <div class="td label">{{ completedLabel }}</div>
      <div class="td">
        <span v-if="status[backup.id] && status[backup.id].end">
          <cv-interactive-tooltip
            alignment="center"
            direction="bottom"
            class="info tooltip-with-text-trigger"
          >
            <template slot="trigger">
              {{
                formatDateDistance(status[backup.id].end * 1000, new Date(), {
                  addSuffix: true,
                })
              }}
            </template>
            <template slot="content">
              {{ (status[backup.id].end * 1000) | date("yyyy-MM-dd HH:mm:ss") }}
            </template>
          </cv-interactive-tooltip>
        </span>
        <span v-else>-</span>
      </div>
    </div>
    <!-- duration -->
    <div class="tr">
      <div class="td label">{{ durationLabel }}</div>
      <div class="td">
        <span
          v-if="
            status[backup.id] &&
            status[backup.id].end &&
            status[backup.id].start
          "
        >
          {{
            (status[backup.id].end - status[backup.id].start) | secondsFormat
          }}
        </span>
        <span v-else>-</span>
      </div>
    </div>
    <!-- total size -->
    <div class="tr">
      <div class="td label">{{ totalSizeLabel }}</div>
      <div class="td">
        <span v-if="status[backup.id] && status[backup.id].total_size">
          {{ status[backup.id].total_size | byteFormat }}
        </span>
        <span v-else>-</span>
      </div>
    </div>
    <!-- total file count -->
    <div class="tr">
      <div class="td label">{{ totalFileCountLabel }}</div>
      <div class="td">
        <span v-if="status[backup.id] && status[backup.id].total_file_count">
          {{ status[backup.id].total_file_count }}
        </span>
        <span v-else>-</span>
      </div>
    </div>
  </div>
</template>

<script>
import DateTimeService from "../lib-mixins/dateTime.js";

export default {
  name: "NsBackupCardDetails",
  mixins: [DateTimeService],
  props: {
    backup: {
      type: Object,
      required: true,
    },
    status: {
      type: Object,
      required: true,
    },
    repositoryLabel: {
      type: String,
      default: "Repository",
    },
    completedLabel: {
      type: String,
      required: true,
    },
    durationLabel: {
      type: String,
      required: true,
    },
    totalSizeLabel: {
      type: String,
      required: true,
    },
    totalFileCountLabel: {
      type: String,
      required: true,
    },
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tooltip";

.ns-backup-card-details {
  // do not render root div, only table rows
  display: contents;
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

.tooltip-with-text-trigger
  ::v-deep
  .bx--tooltip__trigger:not(.bx--btn--icon-only) {
  font-size: 14px;
  color: $interactive-01;
}

// interactive tooltip layout, from ns8-core _core.scss
.cv-interactive-tooltip {
  display: inline-block;
}

.cv-interactive-tooltip ::v-deep .bx--tooltip__label .bx--tooltip__trigger {
  margin-left: 0;
}
</style>
