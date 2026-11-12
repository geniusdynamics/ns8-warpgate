<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div
    :class="[
      `cv-text-input`,
      `ns-text-input`,
      `${carbonPrefix}--form-item`,
      `${carbonPrefix}--text-input-wrapper`,
      { [`${carbonPrefix}--password-input-wrapper`]: isPassword },
    ]"
  >
    <div>
      <label
        :for="uid"
        :class="[
          `${carbonPrefix}--label`,
          {
            [`${carbonPrefix}--label--disabled`]:
              $attrs.disabled !== undefined && $attrs.disabled,
          },
        ]"
      >
        <div class="label-with-tooltip">
          <span>
            {{ label }}
          </span>
          <!-- tooltip -->
          <cv-interactive-tooltip
            v-if="hasTooltipSlot"
            :alignment="tooltipAlignment"
            :direction="tooltipDirection"
            class="info"
          >
            <template slot="content">
              <slot name="tooltip"></slot>
            </template>
          </cv-interactive-tooltip>
        </div>
      </label>
    </div>
    <div
      :class="[
        `${carbonPrefix}--text-input__field-wrapper`,
        {
          [`${carbonPrefix}--text-input__field-wrapper--warning`]:
            !isInvalid && isWarn,
        },
        { 'align-items-center': prefix },
      ]"
      :data-invalid="isInvalid"
    >
      <WarningFilled16
        v-if="isInvalid"
        :class="`${carbonPrefix}--text-input__invalid-icon`"
      />
      <WarningAltFilled16
        v-if="isWarn"
        :class="`${carbonPrefix}--text-input__invalid-icon ${carbonPrefix}--text-input__invalid-icon--warning`"
      />
      <span v-if="prefix" class="prefix">{{ prefix }}</span>
      <input
        :id="uid"
        :class="[
          `${carbonPrefix}--text-input`,
          {
            [`${carbonPrefix}--text-input--light`]: isLight,
            [`${carbonPrefix}--text-input--invalid`]: isInvalid,
            [`${carbonPrefix}--text-input--warning`]: isWarn,
            [`${carbonPrefix}--password-input`]: isPassword,
          },
        ]"
        v-bind="$attrs"
        :value="value"
        v-on="inputListeners"
        :data-toggle-password-visibility="isPassword"
        :type="dataType"
        ref="input"
      />
      <button
        v-if="isPassword"
        :class="[
          `${carbonPrefix}--btn`,
          `${carbonPrefix}--text-input--password__visibility__toggle`,
          `${carbonPrefix}--tooltip__trigger`,
          `${carbonPrefix}--tooltip--a11y`,
          `${carbonPrefix}--tooltip--bottom`,
          `${carbonPrefix}--tooltip--align-end`,
        ]"
        @click="togglePasswordVisibility"
        type="button"
      >
        <span :class="`${carbonPrefix}--assistive-text`">{{
          passwordHideShowLabel
        }}</span>
        <ViewOff16
          v-if="isPasswordVisible"
          :class="`${carbonPrefix}--icon-visibility-off`"
        />
        <View16 v-else :class="`${carbonPrefix}--icon-visibility-off`" />
      </button>
    </div>
    <div :class="`${carbonPrefix}--form-requirement`" v-if="isInvalid">
      <slot name="invalid-message">{{ invalidMessage }}</slot>
    </div>
    <div v-if="isWarn" :class="`${carbonPrefix}--form__requirement`">
      <slot name="warn-text">{{ warnText }}</slot>
    </div>
    <div
      v-if="isHelper"
      :class="[
        `${carbonPrefix}--form__helper-text`,
        { [`${carbonPrefix}--form__helper-text--disabled`]: $attrs.disabled },
      ]"
    >
      <slot name="helper-text">{{ helperText }}</slot>
    </div>
  </div>
</template>

<script>
import { CvTextInput } from "@carbon/vue";
import WarningFilled16 from "@carbon/icons-vue/es/warning--filled/16";
import WarningAltFilled16 from "@carbon/icons-vue/es/warning--alt--filled/16";
import View16 from "@carbon/icons-vue/es/view/16";
import ViewOff16 from "@carbon/icons-vue/es/view--off/16";

export default {
  name: "NsTextInput",
  extends: CvTextInput,
  components: { WarningFilled16, WarningAltFilled16, View16, ViewOff16 },
  props: {
    helperText: { type: String, default: undefined },
    invalidMessage: { type: String, default: undefined },
    label: String,
    passwordHideLabel: { type: String, default: "Hide password" },
    passwordShowLabel: { type: String, default: "Show password" },
    passwordVisible: Boolean,
    type: String,
    value: String,
    warnText: { type: String, default: undefined },
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
    prefix: String,
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

.label-with-tooltip {
  display: flex;
  align-items: baseline;
}

.prefix {
  font-weight: bold;
  margin-right: 0.5rem;
  color: #525252;
}

.align-items-center {
  align-items: center;
}
</style>

<style lang="scss">
// global styles

.ns-text-input .bx--tooltip__label .bx--tooltip__trigger {
  margin-left: 0.25rem;
}
</style>
