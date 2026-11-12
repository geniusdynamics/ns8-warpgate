<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div :class="`ns-byte-slider cv-slider ${carbonPrefix}--form-item`">
    <div class="wrapper" :data-invalid="isInvalid">
      <label
        v-show="label"
        :for="uid"
        :class="[
          `${carbonPrefix}--label`,
          { [`${carbonPrefix}--label--disabled`]: disabled },
        ]"
        :id="labelId"
      >
        {{ label }}
      </label>
      <!-- unlimited/limited radio buttons -->
      <template v-if="showUnlimited">
        <cv-radio-group vertical :class="{ 'unlimited-group': internalUnlimited }">
          <cv-radio-button
            :name="'radio-group-' + uid"
            :label="unlimitedLabel"
            value="unlimited"
            v-model="radioValue"
            :disabled="disabled"
          />
          <cv-radio-button
            :name="'radio-group-' + uid"
            :label="limitedLabel"
            value="limited"
            v-model="radioValue"
            :disabled="disabled"
          />
        </cv-radio-group>
      </template>
      <div v-show="!internalUnlimited">
        <div :class="`${carbonPrefix}--slider-container`">
          <span
            v-if="internalMinLabel"
            :class="`${carbonPrefix}--slider__range-label`"
            >{{ internalMinLabel }}</span
          >
          <div
            :class="[
              `${carbonPrefix}--slider`,
              {
                [`${carbonPrefix}--slider--disabled`]:
                  disabled || internalUnlimited,
              },
            ]"
            data-slider
            data-slider-input-box="#slider-input-box"
          >
            <div
              :class="`${carbonPrefix}--slider__track`"
              @click="onTrackClick"
              ref="track"
            ></div>
            <div
              :class="`${carbonPrefix}--slider__filled-track`"
              :style="`width: ${percentage};`"
            ></div>
            <div
              :class="[
                `${carbonPrefix}--slider__thumb`,
                {
                  [`${carbonPrefix}--slider__thumb--clicked`]: animateClick,
                },
              ]"
              tabindex="0"
              :aria-labelledby="labelId"
              :style="`left: ${percentage};`"
              ref="thumb"
              @keydown.up.right.prevent="onUp"
              @keydown.down.left.prevent="onDown"
              @mousedown="onStartDrag"
            ></div>
            <input
              :id="uid"
              :class="`${carbonPrefix}--slider__input`"
              type="range"
              :step="step"
              :min="min"
              :max="max"
              ref="range"
            />
          </div>
          <span
            v-if="internalMaxLabel"
            :class="`${carbonPrefix}--slider__range-label`"
            >{{ internalMaxLabel }}</span
          >
          <input
            type="number"
            :class="[
              `${carbonPrefix}--text-input ${carbonPrefix}--slider-text-input`,
              {
                [`${carbonPrefix}--text-input--light`]: isLight,
                [`${carbonPrefix}--text-input--invalid`]: isInvalid,
                [`${carbonPrefix}--text-input--warning`]: isWarn,
              },
              ,
              'range-input',
            ]"
            :placeholder="min"
            v-model="internalValue"
            @change="onChange"
            ref="inputBox"
            @keydown.up.prevent="onUp"
            @keydown.down.prevent="onDown"
            :disabled="disabled || internalUnlimited"
          />
          <!-- MiB/GiB toggle -->
          <cv-radio-group v-if="showMibGibToggle" class="mib-gib">
            <cv-radio-button
              v-model="internalByteUnit"
              name="group-mib-gib"
              label="MiB"
              value="mib"
              :disabled="disabled || internalUnlimited"
            />
            <cv-radio-button
              v-model="internalByteUnit"
              name="group-mib-gib"
              label="GiB"
              value="gib"
              :disabled="disabled || internalUnlimited"
            />
          </cv-radio-group>
        </div>
        <!-- human readable label -->
        <NsTag
          v-if="showHumanReadableLabel && !internalUnlimited"
          :label="humanReadableLabel"
          :kind="tagKind"
          :disabled="disabled || internalUnlimited"
          class="human-label"
        >
        </NsTag>
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
  themeMixin,
  carbonPrefixMixin,
  methodsMixin,
} from "@carbon/vue/src/mixins";

export default {
  name: "NsByteSlider",
  mixins: [
    uidMixin,
    themeMixin,
    carbonPrefixMixin,
    methodsMixin({ thumb: ["blur", "focus"] }),
  ],
  props: {
    disabled: Boolean,
    label: String,
    // NOTE: It is not safe to rely on Numbers for non-integer steps
    min: { type: String, default: "0" },
    max: { type: String, default: "100" },
    step: { type: String, default: "1" },
    stepMultiplier: {
      type: String,
      default: "4",
      validator(val) {
        if (val.length) {
          let intMultiplier = parseInt(val);
          if (isNaN(intMultiplier) || intMultiplier < 1) {
            console.warn("ns-byte-slider: multiplier must be >= 1");
            return false;
          }
        }
        return true;
      },
    },
    value: String,
    minLabel: String,
    maxLabel: String,
    showUnlimited: { type: Boolean, default: false },
    isUnlimited: { type: Boolean, default: false },
    byteUnit: { type: String, default: "gib" },
    unlimitedLabel: { type: String, default: "Unlimited" },
    limitedLabel: { type: String, default: "Limited" },
    showHumanReadableLabel: { type: Boolean, default: false },
    showMibGibToggle: { type: Boolean, default: false },
    tagKind: { type: String, default: "high-contrast" },
    invalidMessage: { type: String, default: "" },
  },
  model: {
    prop: "value",
    event: "modelEvent",
  },
  data() {
    return {
      internalValue: "",
      animateClick: false,
      isDragging: false,
      dragStartX: 0,
      dragStartValue: 0,
      percentage: "0%",
      internalByteUnit: "gib",
      isInvalid: false,
      radioValue: "limited",
    };
  },
  computed: {
    labelId() {
      return `${this.uid}-label`;
    },
    internalMinLabel() {
      return this.minLabel !== undefined ? this.minLabel : this.getMin();
    },
    internalMaxLabel() {
      return this.maxLabel !== undefined ? this.maxLabel : this.getMax();
    },
    internalMultiplier() {
      let intMultiplier = parseInt(this.stepMultiplier);
      // default to 4 fro multiplier
      return isNaN(intMultiplier) ? 4 : Math.max(intMultiplier, 1);
    },
    humanReadableLabel() {
      if (this.internalByteUnit === "gib") {
        return this.gibFormat(this.internalValue);
      } else {
        // MiB
        return this.mibFormat(this.internalValue);
      }
    },
    internalUnlimited() {
      return this.radioValue === "unlimited";
    },
  },
  created() {
    this.radioValue = this.isUnlimited ? "unlimited" : "limited";
    this.internalByteUnit = this.byteUnit;
  },
  mounted() {
    this.$refs.range.value = this.value;
    this.internalValue = this.$refs.range.value;
    this.percentage = `${
      ((this.internalValue - this.getMin()) * 100) /
      (this.getMax() - this.getMin())
    }%`;
    this.checkSlots();
  },
  updated() {
    this.checkSlots();
  },
  watch: {
    value(val) {
      this.setValue(val);
    },
    min() {
      this.$nextTick(() => {
        this.setValue(this.internalValue);
      });
    },
    max() {
      this.$nextTick(() => {
        this.setValue(this.internalValue);
      });
    },
    step() {
      this.$nextTick(() => {
        this.setValue(this.internalValue);
      });
    },
    isUnlimited() {
      this.radioValue = this.isUnlimited ? "unlimited" : "limited";
    },
    internalUnlimited() {
      if (this.internalUnlimited) {
        this.$emit("unlimited", true);
      } else {
        this.$emit("unlimited", false);
      }
    },
    byteUnit() {
      this.internalByteUnit = this.byteUnit;
    },
    internalByteUnit() {
      this.$emit("byteUnit", this.internalByteUnit);
    },
  },
  methods: {
    // NOTE: It is not safe to rely on Numbers for non-integer steps
    getMin() {
      if (this.$refs.range) {
        const val = parseFloat(this.$refs.range.min);
        return isNaN(val) ? 0 : val;
      }
      return 0;
    },
    getMax() {
      if (this.$refs.range) {
        const val = parseFloat(this.$refs.range.max);
        return isNaN(val) ? 100 : val;
      }
      return 100;
    },
    getValue() {
      if (this.$refs.range) {
        const val = parseFloat(this.$refs.range.value);
        return isNaN(val) ? 0 : val;
      }
      return (this.getMax() + this.getMin()) / 2;
    },
    getStep() {
      if (this.$refs.range) {
        const val = parseFloat(this.$refs.range.step);
        return isNaN(val) ? 0 : val;
      }
      return 1;
    },

    setValue(newValue) {
      if (this.disabled) return;

      this.$refs.range.value = newValue;
      this.internalValue = this.$refs.range.value;

      this.percentage = `${
        ((this.internalValue - this.getMin()) * 100) /
        (this.getMax() - this.getMin())
      }%`;

      this.$emit("modelEvent", this.$refs.range.value);
      this.$emit("change", this.$refs.range.value);
    },
    onChange() {
      let newValue = this.internalValue.length
        ? parseFloat(this.internalValue)
        : this.getMin();
      this.setValue(newValue);
    },
    onStartDrag(ev) {
      document.body.addEventListener("mousemove", this.onDrag);
      document.body.addEventListener("mouseup", this.onStopDrag);

      this.dragStartX = ev.clientX;
      this.dragStartValue = this.getValue();
      this.isDragging = true;
    },
    onDrag(ev) {
      if (this.isDragging) {
        // percentage change
        let newValue =
          (ev.clientX - this.dragStartX) / this.$refs.track.offsetWidth;
        // uncapped new value
        newValue =
          this.dragStartValue + (this.getMax() - this.getMin()) * newValue;

        this.setValue(newValue, ev);
      }
    },
    onStopDrag() {
      this.isDragging = false;
      document.body.removeEventListener("mousemove", this.onDrag);
      document.body.removeEventListener("mouseup", this.onStopDrag);
    },
    onTrackClick(ev) {
      const afterAnimate = (ev) => {
        if (ev.propertyName === "left") {
          this.animateClick = false;
          this.$refs.thumb.removeEventListener("transitionend", afterAnimate);
        }
      };

      let newValue = ev.offsetX / this.$refs.track.offsetWidth;
      newValue = (this.getMax() - this.getMin()) * newValue + this.getMin();
      this.$refs.thumb.addEventListener("transitionend", afterAnimate);
      this.animateClick = true;

      this.setValue(newValue, ev);
    },
    onUp(ev) {
      let curValue =
        ev.target.type === "number"
          ? parseFloat(ev.target.value)
          : this.getValue();
      let newValue =
        curValue +
        (ev.shiftKey
          ? this.internalMultiplier * this.getStep()
          : this.getStep());
      this.setValue(newValue, ev);
    },
    onDown(ev) {
      let curValue =
        ev.target.type === "number"
          ? parseFloat(ev.target.value)
          : this.getValue();
      let newValue =
        curValue -
        (ev.shiftKey
          ? this.internalMultiplier * this.getStep()
          : this.getStep());
      this.setValue(newValue, ev);
    },
    mibFormat(size) {
      let result;

      switch (true) {
        case size === null || size === "" || isNaN(size):
          result = "-";
          break;

        case size >= 0 && size < 1024:
          result = size + " MiB";
          break;

        case size >= 1024 && size < Math.pow(1024, 2):
          result = Math.round((size / 1024) * 100) / 100 + " GiB";
          break;

        default:
          result = Math.round((size / Math.pow(1024, 2)) * 100) / 100 + " TiB";
      }
      return result;
    },
    gibFormat(size) {
      let result;

      switch (true) {
        case size === null || size === "" || isNaN(size):
          result = "-";
          break;

        case size >= 0 && size < 1024:
          result = size + " GiB";
          break;

        default:
          result = Math.round((size / 1024) * 100) / 100 + " TiB";
      }
      return result;
    },
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
.unlimited-group {
  margin-bottom: 0;
}

.range-input {
  margin-top: 0.5rem !important;
}

.mib-gib {
  margin-left: 1rem;
  margin-top: 0.5rem !important;
  margin-bottom: 0 !important;
}

.human-label {
  margin-top: 1rem;
}

.ns-byte-slider .cv-radio-group.bx--form-item {
  margin-bottom: 0.5rem;
}
</style>

<style lang="scss">
// global styles

.ns-byte-slider .bx--slider-container {
  flex-wrap: wrap;
}

.ns-byte-slider .bx--slider-text-input {
  width: 5rem;
}

.ns-byte-slider .wrapper[data-invalid] ~ .bx--form-requirement {
  display: block;
  overflow: visible;
  max-height: 12.5rem;
  font-weight: 400;
  color: #da1e28;
}
</style>
