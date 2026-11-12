<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-tile kind="standard" :light="light" class="info-card ns-card">
    <!-- overflow menu -->
    <slot v-if="hasMenuSlot" name="menu"></slot>
    <!-- icon -->
    <div v-if="icon" class="row">
      <NsSvg :svg="icon" />
    </div>
    <div v-if="isErrorShown" class="row">
      <NsInlineNotification
        kind="error"
        :title="errorTitle"
        :description="errorDescription"
        :showCloseButton="false"
      />
    </div>
    <div v-else-if="loading" class="row">
      <cv-skeleton-text
        :paragraph="true"
        :line-count="3"
        heading
        class="skeleton"
      ></cv-skeleton-text>
    </div>
    <template v-else>
      <div v-if="title" class="row">
        <h3 :class="['title', wrapTitle ? 'wrap-text' : 'ellipsis']">
          {{ title }}
        </h3>
        <cv-interactive-tooltip
          v-if="$slots.titleTooltip || titleTooltip"
          :alignment="titleTooltipAlignment"
          :direction="titleTooltipDirection"
          class="info title-tooltip"
        >
          <template slot="trigger">
            <Information16 />
          </template>
          <template slot="content">
            <slot v-if="$slots.titleTooltip" name="titleTooltip"></slot>
            <div v-else>{{ titleTooltip }}</div>
          </template>
        </cv-interactive-tooltip>
      </div>
      <div v-if="description" class="row">
        <div class="description">{{ description }}</div>
      </div>
    </template>
    <div class="row slot">
      <!-- Extra content -->
      <slot v-if="hasContentSlot" name="content"></slot>
    </div>
  </cv-tile>
</template>

<script>
import NsSvg from "./NsSvg.vue";
import NsInlineNotification from "./NsInlineNotification.vue";
import Information16 from "@carbon/icons-vue/es/information/16";

export default {
  name: "NsInfoCard",
  components: { NsSvg, NsInlineNotification, Information16 },
  props: {
    title: {
      type: String,
      required: false,
    },
    description: {
      type: String,
      required: false,
    },
    titleTooltip: {
      type: String,
      required: false,
    },
    titleTooltipAlignment: {
      type: String,
      required: false,
      default: "center",
      validator: (val) => ["start", "center", "end"].includes(val),
    },
    titleTooltipDirection: {
      type: String,
      required: false,
      default: "bottom",
      validator: (val) => ["top", "right", "bottom", "left"].includes(val),
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
    loading: Boolean,
    isErrorShown: false,
    errorTitle: String,
    errorDescription: String,
    wrapTitle: Boolean,
    light: Boolean,
  },
  computed: {
    hasMenuSlot() {
      return !!this.$slots.menu;
    },
    hasContentSlot() {
      return !!this.$slots.content;
    },
  },
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tooltip";

.info-card {
  display: flex;
  flex-direction: column;
  min-height: 7rem;
  // needed for abosulute positioning of overflow menu
  position: relative;
}

.skeleton {
  margin-top: 0.5rem;
  margin-left: auto;
  margin-right: auto;
}

.row {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 0.5rem;
}

.title {
  margin-left: 0.25rem;
  margin-right: 0.25rem;
  margin-bottom: 0.5rem;
  text-align: center;
}

.ellipsis {
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}

.wrap-text {
  overflow-wrap: anywhere;
}

.title-tooltip {
  position: relative;
  top: -2px;
}

.description {
  margin-left: 0.25rem;
  margin-right: 0.25rem;
}

.slot {
  margin-top: 0.5rem;
}

// interactive tooltip layout, from ns8-core _core.scss
.cv-interactive-tooltip {
  display: inline-block;
}

.cv-interactive-tooltip ::v-deep .bx--tooltip__label .bx--tooltip__trigger {
  margin-left: 0;
}
</style>
