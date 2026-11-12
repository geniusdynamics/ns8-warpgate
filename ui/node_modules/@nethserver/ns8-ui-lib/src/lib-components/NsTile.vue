<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <component
    :is="tagType"
    :class="[
      `cv-tile ${carbonPrefix}--tile`,
      { [`${carbonPrefix}--tile--light`]: isLight },
      'ns-tile',
      { 'pad-bottom': footerIcon },
      { 'disabled-tile': disabled },
    ]"
    :checked="selected"
    :expanded="expanded"
    v-bind="$attrs"
    v-on="$listeners"
    ref="tile"
  >
    <div :class="['container', { large: large, centered: centered || icon }]">
      <!-- icon -->
      <NsSvg v-if="icon" :svg="icon" class="tile-icon" />

      <template>
        <slot></slot>
      </template>
    </div>

    <!-- footer icon -->
    <NsSvg v-if="footerIcon" :svg="footerIcon" class="tile-footer-icon" />
  </component>
</template>

<script>
import { CvTile } from "@carbon/vue";
import NsSvg from "./NsSvg";

export default {
  name: "NsTile",
  extends: CvTile,
  inheritAttrs: false,
  model: {
    // required for selectable kind
    prop: "modelValue",
    event: "modelEvent",
  },
  components: {
    NsSvg,
  },
  props: {
    // NsTile cannot be expandable
    selected: Boolean,
    kind: {
      type: String,
      default: "standard",
      validator: (value) =>
        ["clickable", "selectable", "standard"].includes(value),
    },
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
    footerIcon: {
      type: [String, Object],
      default: undefined,
      validator(val) {
        if (!val || typeof val === "string") {
          return true;
        }
        return val.render !== null;
      },
    },
    centered: Boolean,
    large: Boolean,
    light: Boolean,
    disabled: Boolean,
  },
  computed: {
    tagType() {
      if (this.disabled) {
        // not selectable nor clickable
        return "cv-tile-standard";
      }

      switch (this.kind) {
        case "clickable":
          return "cv-tile-clickable";
        case "selectable":
          return "cv-tile-selectable";
        default:
          return "cv-tile-standard";
      }
    },
  },
};
</script>

<style scoped lang="scss">
.ns-tile {
  margin-bottom: 2rem;
  position: relative;
}

.container {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.centered {
  text-align: center;
}

.large {
  min-height: 10rem;
}

.tile-icon {
  display: block;
  margin-left: auto;
  margin-right: auto;
  margin-bottom: 1rem;
}

.tile-footer-icon {
  position: absolute;
  right: 1rem;
  bottom: 1rem;
  flex-shrink: 0;
  width: 1.25rem;
  height: 1.25rem;
}

.pad-bottom {
  padding-bottom: 4rem;
}

.disabled-tile {
  color: #c6c6c6;
}
</style>
