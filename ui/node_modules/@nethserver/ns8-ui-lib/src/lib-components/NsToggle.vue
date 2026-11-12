<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div :class="['ns-toggle', { [`${carbonPrefix}--form-item`]: formItem }]">
    <input
      v-bind="$attrs"
      v-on="inputListeners"
      :class="[
        `${carbonPrefix}--toggle-input`,
        { 'bx--toggle-input--small': small },
      ]"
      type="checkbox"
      :id="uid"
      :checked="isChecked === true"
      :aria-checked="`${isChecked}`"
      :value="value"
      ref="input"
    />
    <label
      :class="`${carbonPrefix}--toggle-input__label`"
      :for="uid"
      :aria-label="hiddenLabel"
    >
      <div>
        <span>{{ visibleLabel }}</span>
        <!-- tooltip -->
        <cv-interactive-tooltip
          v-if="hasTooltipSlot && !hideLabel"
          :alignment="tooltipAlignment"
          :direction="tooltipDirection"
          class="tooltip info"
        >
          <template slot="content">
            <slot name="tooltip"></slot>
          </template>
        </cv-interactive-tooltip>
      </div>
      <span :class="`${carbonPrefix}--toggle__switch`">
        <svg
          :class="`${carbonPrefix}--toggle__check`"
          width="6px"
          height="5px"
          viewBox="0 0 6 5"
        >
          <path d="M2.2 2.7L5 0 6 1 2.2 5 0 2.7 1 1.5z" />
        </svg>
        <span :class="`${carbonPrefix}--toggle__text--off`" aria-hidden="true">
          <slot name="text-left">Off</slot>
        </span>
        <span :class="`${carbonPrefix}--toggle__text--on`" aria-hidden="true">
          <slot name="text-right">On</slot>
        </span>
      </span>
    </label>
  </div>
</template>

<script>
import { CvToggle } from "@carbon/vue";

export default {
  name: "NsToggle",
  extends: CvToggle,
  props: {
    small: Boolean,
    label: String,
    formItem: { type: Boolean, default: true },
    hideLabel: Boolean,
    tooltipAlignment: {
      type: String,
      default: "start",
      validator: (val) => ["start", "center", "end"].includes(val),
    },
    tooltipDirection: {
      type: String,
      default: "bottom",
      validator: (val) => ["top", "left", "bottom", "right"].includes(val),
    },
  },
  computed: {
    hasTooltipSlot() {
      return !!this.$slots.tooltip;
    },
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tooltip";

.tooltip {
  display: inline-block;
  position: absolute;
}
</style>

<style lang="scss">
// global styles

.ns-toggle .bx--tooltip__label .bx--tooltip__trigger {
  margin-left: 0.25rem;
}
</style>
