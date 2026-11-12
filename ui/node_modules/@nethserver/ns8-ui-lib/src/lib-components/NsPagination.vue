<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<script>
import { CvPagination } from "@carbon/vue";

export default {
  name: "NsPagination",
  extends: CvPagination,
  props: {
    backwardsButtonDisabled: Boolean,
    forwardsButtonDisabled: Boolean,
    backwardText: { type: String, default: "Prev page" },
    forwardText: { type: String, default: "Next page" },
    pageNumberLabel: { type: String, default: "Page number:" },
    pageSizesLabel: { type: String, default: "Items per page:" },
    numberOfItems: { type: Number, default: Infinity },
    actualItemsOnPage: { type: Number, default: Infinity },
    page: Number,
    pageSizes: { type: Array, default: () => [10, 20, 30, 40, 50] },
    // added
    rangeOfTotalItemsLabel: {
      type: String,
      default: "{range} of {total} items",
    },
    ofTotalPagesLabel: { type: String, default: "of {total} pages" },
  },
  computed: {
    pageOfPages() {
      const { pages, items } = this.ofNPagesProps;

      if (items !== Infinity) {
        return this.ofTotalPagesLabel.replace("{total}", pages);
      }
      return `Page ${this.pageValue}`;
    },
    rangeText() {
      const { start, end, items } = this.rangeProps;

      if (items !== Infinity) {
        // replace {range} and {total} in rangeOfTotalItemsLabel
        return this.rangeOfTotalItemsLabel
          .replace("{range}", `${start}-${end}`)
          .replace("{total}", items);
      } else {
        return `${start}-${end}`;
      }
    },
  },
};
</script>

<style lang="scss">
.cv-pagination .bx--select .bx--label {
  font-size: 100%;
}
</style>
