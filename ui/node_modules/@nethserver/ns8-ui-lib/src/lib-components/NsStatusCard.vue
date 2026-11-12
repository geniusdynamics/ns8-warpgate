<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-tile kind="standard" :light="light" class="status-card ns-card">
    <!-- icon -->
    <div v-if="icon" class="row">
      <NsSvg :svg="icon" />
    </div>
    <div class="row">
      <h3 class="value">{{ value }}</h3>
      <div class="label">{{ label }}</div>
    </div>
    <div class="row">
      <div v-if="valueError" class="stats">
        <NsSvg :svg="ErrorFilled20" class="error-icon" />
        <cv-tooltip
          v-if="errorTooltip"
          :tip="errorTooltip"
          alignment="center"
          direction="bottom"
        >
          <h4>{{ valueError }}</h4>
        </cv-tooltip>
        <h4 v-else>{{ valueError }}</h4>
      </div>
      <div v-if="valueWarning" class="stats">
        <NsSvg :svg="Warning20" class="warning-icon" />
        <cv-tooltip
          v-if="warningTooltip"
          :tip="warningTooltip"
          alignment="center"
          direction="bottom"
        >
          <h4>{{ valueWarning }}</h4>
        </cv-tooltip>
        <h4 v-else>{{ valueWarning }}</h4>
      </div>
      <div v-if="valueSuccess" class="stats">
        <NsSvg :svg="CheckmarkFilled20" class="success-icon" />
        <cv-tooltip
          v-if="successTooltip"
          :tip="successTooltip"
          alignment="center"
          direction="bottom"
        >
          <h4>{{ valueSuccess }}</h4>
        </cv-tooltip>
        <h4 v-else>{{ valueSuccess }}</h4>
      </div>
    </div>
  </cv-tile>
</template>

<script>
import CheckmarkFilled20 from "@carbon/icons-vue/es/checkmark--filled/20";
import ErrorFilled20 from "@carbon/icons-vue/es/error--filled/20";
import Warning20 from "@carbon/icons-vue/es/warning--filled/20";
import NsSvg from "./NsSvg.vue";
import { CvTile, CvTooltip } from "@carbon/vue";

export default {
  name: "NsStatusCard",
  //components added for storybook to work
  components: { NsSvg, CvTile, CvTooltip },
  props: {
    value: {
      type: [Number, String],
      required: true,
    },
    valueSuccess: [Number, String],
    valueError: [Number, String],
    valueWarning: [Number, String],
    label: String,
    errorTooltip: String,
    successTooltip: String,
    warningTooltip: String,
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
  data() {
    return {
      CheckmarkFilled20,
      ErrorFilled20,
      Warning20,
    };
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tokens";

.status-card {
  display: flex;
  flex-direction: column;
}

.row {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.5rem;
}

.value {
  margin-left: 0.25rem;
  margin-right: 0.25rem;
}

.label {
  margin-left: 0.25rem;
  margin-right: 0.25rem;
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
