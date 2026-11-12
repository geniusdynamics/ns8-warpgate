<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div class="base-timer" :style="{ height: size + 'px', width: size + 'px' }">
    <svg
      class="base-timer__svg"
      viewBox="0 0 100 100"
      xmlns="http://www.w3.org/2000/svg"
    >
      <g class="base-timer__circle">
        <path
          id="base-timer-path-remaining"
          stroke-dasharray="251"
          class="base-timer__path-remaining green"
          d="
            M 50, 50
            m -40, 0
            a 40,40 0 1,0 80,0
            a 40,40 0 1,0 -80,0
          "
          :style="{
            'stroke-width': strokeWidth + 'px',
            'stroke-dasharray': circleDasharray,
            color: color,
          }"
        ></path>
      </g>
    </svg>
  </div>
</template>

<script>
export default {
  name: "NsCircleTimer",
  props: {
    timeLimit: {
      type: Number, // milliseconds
      required: true,
    },
    size: {
      type: Number,
      default: 16,
    },
    strokeWidth: {
      type: Number,
      default: 20,
    },
    color: {
      type: String,
      default: "#00a2de",
    },
  },
  data() {
    return {
      timerInterval: null,
      timePassed: 0,
      timeLeft: -1,
      // length = 2πr = 2 * π * 40 = 251
    };
  },
  computed: {
    circleDasharray() {
      return `${(this.calculateTimeFraction() * 251).toFixed(0)} 251`;
    },
  },
  created() {
    this.timeLimitSeconds = this.timeLimit / 1000;
    this.timeLeft = this.timeLimitSeconds;

    this.$nextTick(() => {
      this.timePassed += 1;
      this.timeLeft = this.timeLimitSeconds - this.timePassed;
    });

    this.timerInterval = setInterval(() => {
      this.timePassed += 1;
      this.timeLeft = this.timeLimitSeconds - this.timePassed;
    }, 1000);
  },
  beforeDestroy() {
    clearInterval(this.timerInterval);
  },
  methods: {
    calculateTimeFraction() {
      return this.timeLeft / this.timeLimitSeconds;
    },
  },
};
</script>

<style scoped lang="scss">
.base-timer {
  position: relative;
}

.base-timer__circle {
  fill: none;
  stroke: none;
}

.base-timer__path-remaining {
  stroke: currentColor;

  /* animation starts at the top of the circle */
  transform: rotate(90deg);
  transform-origin: center;

  /* one second aligns with the speed of the countdown timer */
  transition: 1s linear all;
}

.base-timer__svg {
  /* flips the svg and makes the animation to move left-to-right */
  transform: scaleX(-1);
}
</style>
