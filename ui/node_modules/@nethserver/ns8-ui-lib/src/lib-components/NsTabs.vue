<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<script>
import { CvTabs } from "@carbon/vue";

export default {
  name: "NsTabs",
  extends: CvTabs,
  methods: {
    // extend method to fix error on beforeDestroy
    doScrollIntoView(index) {
      const tab = this.$refs.link[index];

      // fix error on beforeDestroy
      if (!tab) {
        return;
      }

      const scrollContainer = tab.parentNode ? tab.parentNode.parentNode : null;
      let newScrollLeft;

      if (tab && scrollContainer) {
        const scrollLeft = scrollContainer.scrollLeft;
        const tabLeft = tab.offsetLeft - scrollContainer.offsetLeft;

        if (index === 0) {
          newScrollLeft = 0;
        } else if (index === this.$refs.link.length - 1) {
          newScrollLeft =
            scrollContainer.scrollWidth - scrollContainer.offsetWidth;
        } else if (tabLeft < scrollLeft) {
          newScrollLeft = tabLeft;
        } else {
          const rightOfTab =
            tab.offsetLeft - scrollContainer.offsetLeft + tab.offsetWidth;
          if (rightOfTab > scrollContainer.offsetWidth + scrollLeft) {
            newScrollLeft = rightOfTab - scrollContainer.offsetWidth;

            if (!this.rightOverflowNavButtonHidden) {
              newScrollLeft += this.OVERFLOW_BUTTON_OFFSET;
            }
          }
        }
      }

      if (newScrollLeft !== undefined) {
        this.skipScroll = true;
        this.leftOverflowNavButtonHidden = newScrollLeft <= 0;
        this.rightOverflowNavButtonHidden =
          newScrollLeft + this.$refs.tablist.clientWidth >=
          this.$refs.tablist.scrollWidth;

        this.$nextTick(() => {
          // allow left and right nav hide to propegate before setting scroll
          scrollContainer.scrollLeft = newScrollLeft;
          this.skipScroll = false;
        });
      }
    },
  },
};
</script>
