<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <component
    :is="!isFilter && hasClickListener ? 'button' : 'div'"
    v-on="this.$listeners"
    :id="uid"
    :class="[
      `cv-tag ${carbonPrefix}--tag`,
      `${carbonPrefix}--tag--${tagKind}`,
      {
        [`${carbonPrefix}--tag--disabled`]: disabled,
        [`${carbonPrefix}--tag--filter`]: isFilter,
        [`${carbonPrefix}--tag--${size}`]: size,
      },
    ]"
    :title="title"
    @keydown.enter.stop.prevent="$emit('remove')"
    @keydown.space.prevent
    @keyup.space.prevent="$emit('remove')"
  >
    <div v-if="icon && !filter" :class="`${carbonPrefix}--tag__custom-icon`">
      <CvSvg :svg="icon" />
    </div>
    <span :class="`${carbonPrefix}--tag__label`">{{ label }}</span>
    <button
      v-if="isFilter"
      :class="`${carbonPrefix}--tag__close-icon`"
      :aria-label="clearAriaLabel"
      :title="clearAriaLabel"
      @click.stop.prevent="onRemove"
      :disabled="disabled"
    >
      <Close16 />
    </button>
  </component>
</template>

<script>
import { CvTag } from "@carbon/vue";

export default {
  name: "NsTag",
  extends: CvTag,
  computed: {
    title() {
      return null;
    },
  },
};
</script>

<style scoped lang="scss">
.bx--tag--filter {
  cursor: default;
}
</style>
