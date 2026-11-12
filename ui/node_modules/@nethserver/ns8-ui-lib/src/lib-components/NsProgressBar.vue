<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <!-- indeterminate -->
  <div class="progress-bar-container" :style="heightStyle">
    <div class="slider" :style="heightStyle">
      <template v-if="indeterminate">
        <div class="indeterminate-line" :style="heightStyle"></div>
        <div class="indeterminate-subline inc" :style="heightStyle"></div>
        <div class="indeterminate-subline dec" :style="heightStyle"></div>
      </template>
      <template v-else>
        <div
          :class="[
            'line',
            {
              healthy: healthyStatus,
              warning: warningStatus,
              danger: dangerStatus,
            },
          ]"
          :style="heightStyle"
        ></div>
        <div
          :class="[
            'progress-line',
            {
              healthy: healthyStatus,
              warning: warningStatus,
              danger: dangerStatus,
            },
          ]"
          :style="progressLineStyle"
        ></div>
      </template>
    </div>
  </div>
</template>

<script>
export default {
  name: "NsProgressBar",
  props: {
    value: {
      // a number between 0 and 100
      type: [String, Number],
      default: 0,
    },
    indeterminate: {
      type: Boolean,
      default: false,
    },
    height: {
      type: String,
      default: "5px",
    },
    warningThreshold: { type: Number, default: 70 },
    dangerThreshold: { type: Number, default: 90 },
    useStatusColors: { type: Boolean, default: false },
    useHealthyColor: { type: Boolean, default: true },
  },
  data() {
    return {
      progressLineStyle: {
        width: this.numericValue + "%",
        transition: "width 0.3s",
        height: this.height,
      },
      heightStyle: {
        height: this.height,
      },
    };
  },
  created() {
    this.progressLineStyle.width = this.numericValue + "%";
    this.heightStyle.height = this.height;
  },
  computed: {
    numericValue() {
      return Number(this.value) || 0;
    },
    healthyStatus() {
      return (
        this.useStatusColors &&
        this.useHealthyColor &&
        this.numericValue < this.warningThreshold
      );
    },
    warningStatus() {
      return (
        this.useStatusColors &&
        this.numericValue >= this.warningThreshold &&
        this.numericValue < this.dangerThreshold
      );
    },
    dangerStatus() {
      return this.useStatusColors && this.numericValue >= this.dangerThreshold;
    },
  },
  watch: {
    value: function () {
      this.progressLineStyle.width = this.numericValue + "%";
    },
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tokens";

.progress-bar-container {
  width: 100%;
  position: relative;
}

.slider {
  position: absolute;
  width: 100%;
  overflow-x: hidden;
}

.line {
  position: absolute;
  opacity: 0.4;
  width: 100%;
}

.progress-line {
  position: absolute;
}

.indeterminate-line {
  position: absolute;
  opacity: 0.4;
  width: 150%;
}

.indeterminate-subline {
  position: absolute;
}
.inc {
  animation: increase 2s infinite;
}
.dec {
  animation: decrease 2s 0.5s infinite;
}

// branding colors
.line,
.progress-line,
.indeterminate-line,
.indeterminate-subline {
  background: $interactive-01;
}

.line.healthy,
.progress-line.healthy,
.indeterminate-line.healthy,
.indeterminate-subline.healthy {
  background: $support-02;
}

.line.warning,
.progress-line.warning,
.indeterminate-line.warning,
.indeterminate-subline.warning {
  background: $ns-warning-status-color;
}

.line.danger,
.progress-line.danger,
.indeterminate-line.danger,
.indeterminate-subline.danger {
  background: $danger-01;
}

@keyframes increase {
  from {
    left: -5%;
    width: 5%;
  }
  to {
    left: 130%;
    width: 100%;
  }
}
@keyframes decrease {
  from {
    left: -80%;
    width: 80%;
  }
  to {
    left: 110%;
    width: 10%;
  }
}
</style>
