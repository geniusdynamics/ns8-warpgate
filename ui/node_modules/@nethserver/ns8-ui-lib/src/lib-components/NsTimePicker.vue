<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div :class="`ns-time-picker cv-time-picker ${carbonPrefix}--form-item`">
    <div
      :class="[
        `${carbonPrefix}--time-picker`,
        { [`${carbonPrefix}--time-picker--light`]: isLight },
      ]"
      :data-invalid="isInvalid"
    >
      <div :class="`${carbonPrefix}--time-picker__input`">
        <label :for="uid" :class="`${carbonPrefix}--label`">{{ label }}</label>
        <vue-timepicker
          :id="uid"
          :hide-clear-button="hideClearButton"
          v-bind="$attrs"
          :value="value"
          :drop-direction="dropDirection"
          @input="$emit('input', $event)"
          :class="[
            `time-picker-field ${carbonPrefix}--time-picker__input-field ${carbonPrefix}--text-input`,
            { [`${carbonPrefix}--text-input--light`]: isLight },
            { 'narrow-width': hideClearButton },
          ]"
        ></vue-timepicker>
      </div>
    </div>
    <div :class="`${carbonPrefix}--form-requirement`" v-if="isInvalid">
      <slot name="invalid-message">{{ invalidMessage }}</slot>
    </div>
  </div>
</template>

<script>
import {
  uidMixin,
  carbonPrefixMixin,
  themeMixin,
} from "@carbon/vue/src/mixins";

export default {
  name: "NsTimePicker",
  mixins: [uidMixin, carbonPrefixMixin, themeMixin],
  props: {
    value: String,
    label: { type: String, default: "hh:mm" },
    hideClearButton: {
      type: Boolean,
      default: false,
    },
    invalidMessage: {
      type: String,
      default: "",
    },
    dropDirection: {
      type: String,
      default: "down",
      validator: (val) => ["up", "down", "auto"].includes(val),
    }
  },
  data() {
    return {
      isInvalid: false,
    };
  },
  mounted() {
    this.checkSlots();
  },
  updated() {
    this.checkSlots();
  },
  methods: {
    checkSlots() {
      // NOTE: this.$slots is not reactive so needs to be managed on updated
      this.isInvalid = !!(
        this.$slots["invalid-message"] ||
        (this.invalidMessage && this.invalidMessage.length)
      );
    },
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tokens";

.ns-time-picker .time-picker-field {
  padding: 0;
  width: 6rem;
}

// reduce width if clear button is hidden
.ns-time-picker .time-picker-field.narrow-width {
  width: 4.875rem;
}

// brand color outline on focus
.ns-time-picker .time-picker-field ::v-deep input:active,
.ns-time-picker .time-picker-field ::v-deep input:focus {
  outline: 2px solid $interactive-01;
  outline-offset: -2px;
}

// hover color for clear button
.ns-time-picker .time-picker-field ::v-deep .clear-btn:hover {
  color: $ui-05;
}

// background color of selected time inside dropdown
.ns-time-picker
  .time-picker-field
  ::v-deep
  .dropdown
  ul
  li:not([disabled]).active,
.ns-time-picker
  .time-picker-field
  ::v-deep
  .dropdown
  ul
  li:not([disabled]).active:focus,
.ns-time-picker
  .time-picker-field
  ::v-deep
  .dropdown
  ul
  li:not([disabled]).active:hover {
  background-color: $interactive-01;
}
</style>

<style lang="scss">
// global styles

// hide default black outline
.ns-time-picker .time-picker-field,
.ns-time-picker .time-picker-field:active,
.ns-time-picker .time-picker-field:focus {
  outline: none;
}

.ns-time-picker .time-picker-field input {
  height: 100% !important;
  background: none !important;
  border: none !important;
  padding: 0 1rem !important;
  font-family: "IBM Plex Mono", "Menlo", "DejaVu Sans Mono",
    "Bitstream Vera Sans Mono", Courier, monospace !important;
  font-size: 0.875rem !important;
  font-weight: 400 !important;
  width: 6rem !important;
  letter-spacing: 0.32px;
}

// reduce width if clear button is hidden
.ns-time-picker .time-picker-field.narrow-width input {
  width: 4.875rem !important;
}

// adjust clear button style
.ns-time-picker .time-picker-field .clear-btn {
  color: #797979;
  padding-right: 1rem;
}

// adjust position of dropdown - direction down
.ns-time-picker .vue__time-picker .dropdown.drop-down {
  top: 2.5rem;
}

// adjust position of dropdown - direction up
.ns-time-picker .vue__time-picker .dropdown.drop-up {
  bottom: 2.5rem;
}

// hide HH and mm labels inside dropdown
.ns-time-picker .time-picker-field .dropdown .hint {
  display: none;
}
</style>
