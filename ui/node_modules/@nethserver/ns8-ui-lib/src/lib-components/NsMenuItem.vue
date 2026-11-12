<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div class="ns-menu-item">
    <span v-if="icon" class="icon"><NsSvg :svg="icon" /></span>
    <span v-else-if="hasIconSlot" class="icon">
      <slot name="icon"></slot>
    </span>
    <span>{{ label }}</span>
  </div>
</template>

<script>
import NsSvg from "./NsSvg.vue";

export default {
  name: "NsMenuItem",
  components: {
    NsSvg,
  },
  props: {
    label: {
      type: String,
      required: true,
    },
    icon: {
      type: Object,
    },
  },
  computed: {
    hasIconSlot() {
      return !!this.$slots.icon;
    },
  },
};
</script>

<style scoped lang="scss">
.ns-menu-item {
  display: flex;
  align-items: center;
}

.icon {
  margin-right: 0.5rem;
}
</style>
