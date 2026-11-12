<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div>
    <div class="mg-bottom-sm">
      <span class="label">{{ label }}</span>
      <span>{{
        loading || Number.isNaN(Number(value)) ? "-" : value + "%"
      }}</span>
    </div>
    <NsProgressBar
      :value="value"
      :indeterminate="loading"
      :useStatusColors="true"
      :warningThreshold="warningThreshold"
      :dangerThreshold="dangerThreshold"
      :height="progressBarHeight"
    />
  </div>
</template>

<script>
import NsProgressBar from "./NsProgressBar.vue";

export default {
  name: "NsMeterChart",
  components: { NsProgressBar },
  props: {
    label: { type: String, required: true },
    value: { type: [String, Number], default: 0 },
    loading: { type: Boolean, default: false },
    progressBarHeight: { type: String, default: "10px" },
    // default value of following props is defined in NsProgressBar
    warningThreshold: { type: Number, default: undefined },
    dangerThreshold: { type: Number, default: undefined },
  },
};
</script>

<style scoped lang="scss">
.label {
  font-weight: bold;
  margin-right: 0.5rem;
}

.mg-bottom-sm {
  margin-bottom: 0.5rem !important;
}
</style>
