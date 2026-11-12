<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div class="empty-state">
    <NsLottieAnimation
      v-if="animationData"
      :animationData="animationData"
      :refName="animationTitle"
      :animateOnHover="true"
      :loop="loop"
      :autoPlay="true"
      class="animation image"
    />
    <NsPictogram v-else title="empty state" class="image">
      <template v-if="hasPictogramSlot">
        <slot name="pictogram"></slot>
      </template>
      <template v-else>
        <ExclamationMarkPictogram />
      </template>
    </NsPictogram>
    <h5 class="title">{{ title }}</h5>

    <template v-if="hasDescriptionSlot">
      <div class="description">
        <slot name="description"></slot>
      </div>
    </template>
  </div>
</template>

<script>
import NsPictogram from "./NsPictogram.vue";
import NsLottieAnimation from "./NsLottieAnimation";
import ExclamationMarkPictogram from "./pictograms/ExclamationMarkPictogram";

export default {
  name: "NsEmptyState",
  components: { NsPictogram, ExclamationMarkPictogram, NsLottieAnimation },
  props: {
    title: {
      type: String,
      required: true,
    },
    animationData: Object,
    animationTitle: String,
    loop: {
      type: [Boolean, Number],
      default: 1,
    },
  },
  computed: {
    hasPictogramSlot() {
      return !!this.$slots.pictogram;
    },
    hasDescriptionSlot() {
      return !!this.$slots.description;
    },
  },
};
</script>

<style scoped lang="scss">
.empty-state {
  text-align: center;
  padding: 2rem;
}

.empty-state .image {
  margin-bottom: 1rem;
}

.empty-state .description {
  margin-top: 1rem;
}

.animation {
  display: inline-block;
  width: 64px;
  height: 64px;
}
</style>
