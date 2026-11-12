<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div
    data-modal
    :id="uid"
    :class="[
      `cv-modal ${carbonPrefix}--modal`,
      {
        'is-visible': dataVisible,
        [`${carbonPrefix}--modal--danger`]: kind === 'danger',
      },
    ]"
    tabindex="-1"
    @keydown.esc.prevent="onEsc"
    @click.self="onExternalClick"
  >
    <div
      :class="[
        `${carbonPrefix}--modal-container`,
        { [`${carbonPrefix}--modal-container--${internalSize}`]: internalSize },
      ]"
      v-bind="dialogAttrs"
      ref="modalDialog"
    >
      <div
        class="cv-modal__before-content"
        ref="beforeContent"
        tabindex="0"
        style="position: absolute; height: 1px; width: 1px; left: -9999px"
        @focus="focusBeforeContent"
      />
      <div :class="`${carbonPrefix}--modal-header`">
        <p :class="`${carbonPrefix}--modal-header__label`">
          <slot name="label"></slot>
        </p>
        <p :class="`${carbonPrefix}--modal-header__heading`">
          <slot name="title">Modal Title</slot>
        </p>
        <button
          :class="`${carbonPrefix}--modal-close`"
          type="button"
          @click="onClose"
          ref="close"
          :aria-label="closeAriaLabel"
        >
          <Close16 :class="`${carbonPrefix}--modal-close__icon`" />
        </button>
      </div>

      <div
        :class="[
          `${carbonPrefix}--modal-content`,
          { [`${carbonPrefix}--modal-content--with-form`]: hasFormContent },
        ]"
        ref="content"
        :tabindex="scrollable ? 0 : undefined"
      >
        <slot name="content"></slot>
      </div>

      <cv-button-set
        :class="[
          `${carbonPrefix}--modal-footer`,
          {
            [`${carbonPrefix}--modal-footer--three-button`]:
              hasPrimary && hasSecondary && hasOtherBtn,
          },
        ]"
        v-if="hasFooter"
      >
        <cv-button
          type="button"
          kind="secondary"
          @click="onOtherBtnClick"
          v-if="hasOtherBtn"
          ref="otherBtn"
        >
          <slot name="other-button">Other button</slot>
        </cv-button>
        <cv-button
          type="button"
          kind="secondary"
          @click="onSecondaryClick"
          v-if="hasSecondary"
          ref="secondary"
        >
          <slot name="secondary-button">Secondary button</slot>
        </cv-button>
        <NsButton
          :disabled="primaryButtonDisabled"
          type="button"
          :kind="primaryKind"
          @click="onPrimaryClick"
          v-if="hasPrimary"
          ref="primary"
          :loading="isLoading"
        >
          <slot name="primary-button">Primary button</slot>
        </NsButton>
      </cv-button-set>
      <div
        class="cv-modal__after-content"
        ref="afterContent"
        tabindex="0"
        style="position: absolute; height: 1px; width: 1px; left: -9999px"
        @focus="focusAfterContent"
      />
    </div>
  </div>
</template>

<script>
import { CvModal } from "@carbon/vue";
import NsButton from "./NsButton";

export default {
  name: "NsModal",
  extends: CvModal,
  components: {
    CvModal,
    NsButton,
  },
  props: {
    hideOnClickOutside: {
      type: Boolean,
      default: false,
    },
    isLoading: {
      type: Boolean,
      default: false,
    },
    alert: Boolean,
    closeAriaLabel: { type: String, default: "Close modal" },
    kind: {
      type: String,
      default: "",
      validator: (val) => ["", "danger"].includes(val),
    },
    autoHideOff: Boolean,
    visible: Boolean,
    primaryButtonDisabled: Boolean,
    size: String,
    hasFormContent: Boolean,
  },
  methods: {
    onExternalClick(ev) {
      if (this.hideOnClickOutside) {
        if (ev.target === this.$el) {
          this._maybeHide(ev, "external-click");
        }
      }
    },
  },
  focusBeforeContent() {
    this.$nextTick(() => {
      if (this.$slots["primary-button"] && !this.primaryButtonDisabled) {
        this.$refs.primary.$el.focus();
      } else if (this.$slots["secondary-button"]) {
        this.$refs.secondary.$el.focus();
      } else if (this.$slots["other-button"]) {
        this.$refs.otherBtn.$el.focus();
      } else {
        this.$refs.close.focus();
      }
    });
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/modal";
</style>
