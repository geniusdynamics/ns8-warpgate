<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div data-overflow-menu :class="[`cv-overflow-menu`]" :id="uid">
    <button
      :class="[
        `bx--btn--${lowerCaseKind}`,
        'bx--btn',
        'bx--btn--field',
        {
          [`${carbonPrefix}--overflow-menu--open`]: open,
        },
      ]"
      aria-haspopup
      type="button"
      :aria-expanded="open ? 'true' : 'false'"
      :aria-controls="`${uid}-menu`"
      :id="`${uid}-trigger`"
      ref="trigger"
      @click="doToggle"
      @keydown.space.prevent
      @keyup.space.prevent="doToggle"
      @keydown.enter.prevent="doToggle"
      @keydown.tab="onOverflowMenuTab"
    >
      <slot name="trigger"> </slot>
      <NsSvg :svg="ChevronDown20" :class="`${carbonPrefix}--btn__icon`" />
    </button>
    <div
      :class="[
        `${carbonPrefix}--overflow-menu-options`,
        {
          [`${carbonPrefix}--overflow-menu-options--open`]: open,
        },
      ]"
      tabindex="-1"
      ref="popup"
      :aria-labelledby="`${uid}-trigger`"
      :id="`${uid}-menu`"
      :style="{ left: left + 'px', top: top + 'px' }"
      @focusout="checkFocusOut"
      @mousedown.prevent="preventFocusOut"
    >
      <ul :class="`${carbonPrefix}--overflow-menu-options__content`">
        <slot></slot>
      </ul>
      <div
        class="cv-overflow-menu__after-content"
        ref="afterContent"
        tabindex="0"
        style="position: absolute; height: 1px; width: 1px; left: -9999px"
        @focus="focusAfterContent"
      />
    </div>
  </div>
</template>

<script>
import { CvOverflowMenu } from "@carbon/vue";
import NsSvg from "./NsSvg.vue";
import IconService from "../lib-mixins/icon.js";

export default {
  name: "NsDropdownAction",
  extends: CvOverflowMenu,
  components: { NsSvg },
  mixins: [IconService],
  props: {
    kind: {
      type: String,
      default: "secondary",
      validator: (val) =>
        [
          "default",
          "primary",
          "secondary",
          "tertiary",
          "ghost",
          "danger",
          "danger--ghost",
          "danger--tertiary",
        ].includes(val),
    },
    up: Boolean,
    offset: {
      type: Object,
      validator(value) {
        return value && value.left !== undefined && value.top !== undefined;
      },
    },
  },
  computed: {
    lowerCaseKind() {
      return this.kind.toLowerCase();
    },
  },
};
</script>

<style scoped lang="scss"></style>
