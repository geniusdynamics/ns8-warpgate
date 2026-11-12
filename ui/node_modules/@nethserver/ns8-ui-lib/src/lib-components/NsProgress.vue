<!--
  Copyright (C) 2025 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div class="ns-progress">
    <div
      v-for="(s, index) in steps"
      :key="s.id"
      :class="['step', { 'step-complete-or-current': stepNumber >= index }]"
    >
      <CheckmarkOutline16 v-if="stepNumber > index" class="icon primary" />
      <CircleFilled16 v-else-if="stepNumber === index" class="icon primary" />
      <RadioButton16 v-else class="icon" />
      <span>{{ s.label }}</span>
    </div>
  </div>
</template>

<script>
import CircleFilled16 from "@carbon/icons-vue/es/circle--filled/16";
import CheckmarkOutline16 from "@carbon/icons-vue/es/checkmark--outline/16";
import RadioButton16 from "@carbon/icons-vue/es/radio-button/16";

export default {
  name: "NsProgress",
  components: {
    CheckmarkOutline16,
    CircleFilled16,
    RadioButton16,
  },
  props: {
    stepId: {
      type: String,
      required: true,
    },
    steps: { type: Array, default: () => [] },
  },
  computed: {
    stepNumber() {
      return this.steps.findIndex((s) => s.id === this.stepId);
    },
  },
};
</script>

<style scoped lang="scss">
.ns-progress {
  display: flex;
  justify-content: space-between;
}

.step {
  display: flex;
  flex: 1;
  gap: 0.5rem;
  border-top: 2px solid #e0e0e0;
  padding-top: 0.5rem;
}

.step-complete-or-current {
  border-top: 2px solid #00a2de;
}

.icon {
  flex-shrink: 0;
  margin-left: 0.5rem;
}

.primary {
  color: #00a2de;
}
</style>
