<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div class="ns-lottie-animation" @mouseover="onMouseOver">
    <LottieAnimation
      :ref="refName"
      :animationData="animationData"
      :loop="loop"
      :autoPlay="autoPlay"
      @loopComplete="onLoopComplete"
      @complete="onComplete"
      @enterFrame="onEnterFrame"
    />
  </div>
</template>

<script>
import LottieAnimation from "lottie-web-vue";

export default {
  name: "NsLottieAnimation",
  components: { LottieAnimation },
  props: {
    animationData: {
      type: Object,
      required: true,
    },
    loop: {
      type: [Boolean, Number],
      default: false,
    },
    autoPlay: {
      type: Boolean,
      default: true,
    },
    refName: {
      type: String,
      default: "anim",
    },
    animateOnHover: {
      type: Boolean,
      default: true,
    },
  },
  methods: {
    onLoopComplete(eventData) {
      this.$emit("loopComplete", eventData);
    },
    onComplete(eventData) {
      this.$emit("complete", eventData);

      if (this.animateOnHover) {
        this.$refs[this.refName].stop();
      }
    },
    onEnterFrame(eventData) {
      this.$emit("enterFrame", eventData);
    },
    onMouseOver(eventData) {
      this.$emit("mouseover", eventData);

      if (this.animateOnHover) {
        this.$refs[this.refName].play();
      }
    },
  },
};
</script>

<style scoped lang="scss"></style>
