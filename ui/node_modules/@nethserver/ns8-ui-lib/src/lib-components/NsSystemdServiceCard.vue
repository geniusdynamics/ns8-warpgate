<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-tile kind="standard" :light="light" class="service-card ns-card">
    <!-- icon -->
    <div v-if="icon" class="row">
      <NsSvg :svg="icon" />
    </div>
    <div class="row">
      <h3 class="service-name">{{ serviceName }}</h3>
    </div>
    <div class="row">
      <div class="stats">
        <cv-tag v-if="failed" kind="red" :label="failedLabel"></cv-tag>
        <cv-tag v-if="active" kind="green" :label="activeLabel"></cv-tag>
        <cv-tag v-else kind="gray" :label="inactiveLabel"></cv-tag>
        <cv-tag v-if="enabled" kind="blue" :label="enabledLabel"></cv-tag>
        <cv-tag v-else kind="gray" :label="disaledLabel"></cv-tag>
      </div>
    </div>
  </cv-tile>
</template>

<script>
import NsSvg from "./NsSvg.vue";
import { CvTile, CvTag } from "@carbon/vue";

export default {
  name: "NsSystemdServiceCard",
  //components added for storybook to work
  components: { NsSvg, CvTile, CvTag },
  props: {
    serviceName: {
      type: String,
      required: true,
    },
    active: Boolean,
    failed: Boolean,
    enabled: Boolean,
    failedLabel: {
      type: String,
      default: "failed",
    },
    activeLabel: {
      type: String,
      default: "active",
    },
    inactiveLabel: {
      type: String,
      default: "inactive",
    },
    enabledLabel: {
      type: String,
      default: "enabled",
    },
    disaledLabel: {
      type: String,
      default: "disabled",
    },
    icon: {
      type: [String, Object],
      default: undefined,
      validator(val) {
        if (!val || typeof val === "string") {
          return true;
        }
        return val.render !== null;
      },
    },
    light: Boolean,
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tokens";

.service-card {
  display: flex;
  flex-direction: column;
}

.row {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.5rem;
}

.service-name {
  margin-left: 0.25rem;
  margin-right: 0.25rem;
  margin-bottom: 0.5rem;
  text-align: center;
  overflow-wrap: anywhere;
}

.success-icon {
  color: $support-02;
  margin-right: 0.25rem;
}

.error-icon {
  color: $danger-01;
  margin-right: 0.25rem;
}

.warning-icon {
  color: $ns-warning-status-color;
  margin-right: 0.25rem;
}

.stats {
  display: flex;
  align-items: center;
  margin-left: 0.5rem;
  margin-right: 0.5rem;
}
</style>
