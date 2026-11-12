<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div class="ns-data-table">
    <cv-search
      v-if="isSearchable && !isErrorShown"
      :label="searchLabel"
      :placeholder="searchPlaceholder"
      :clear-aria-label="searchClearLabel"
      v-model="searchFilter"
      v-debounce="filterRows"
      :disabled="isLoading"
      @input="onSearchInput"
      :light="false"
      ref="tableSearch"
    >
    </cv-search>
    <NsInlineNotification
      v-if="isErrorShown"
      kind="error"
      :title="errorTitle"
      :description="errorDescription"
      :showCloseButton="false"
    />
    <!-- loading data -->
    <cv-data-table-skeleton
      v-else-if="isLoading"
      :columns="columns"
      :rows="skeletonRows"
    ></cv-data-table-skeleton>
    <!-- empty state -->
    <template v-else-if="!allRows.length">
      <cv-tile>
        <slot name="empty-state"></slot>
      </cv-tile>
    </template>
    <!-- no search results -->
    <cv-tile v-else-if="!filteredRows.length">
      <NsEmptyState
        :title="noSearchResultsLabel"
        :animationData="GhostLottie"
        animationTitle="ghost"
        :loop="1"
      >
        <template #description>
          <div>{{ noSearchResultsDescription }}</div>
        </template>
      </NsEmptyState>
    </cv-tile>
    <!-- data table -->
    <div v-else :style="tableStyle" class="cv-data-table">
      <div :class="`${carbonPrefix}--data-table-container`">
        <div
          v-if="hasTableHeader"
          :class="`${carbonPrefix}--data-table-header`"
        >
          <h4 :class="`${carbonPrefix}--data-table-header__title`" v-if="title">
            {{ title }}
          </h4>
          <p
            v-if="isHelper"
            :class="`${carbonPrefix}--data-table-header__description`"
          >
            <slot name="helper-text">{{ helperText }}</slot>
          </p>
        </div>

        <section v-if="hasToolbar" :class="`${carbonPrefix}--table-toolbar`">
          <div
            :aria-hidden="!batchActive"
            v-show="hasBatchActions"
            :class="[
              `${carbonPrefix}--batch-actions`,
              { [`${carbonPrefix}--batch-actions--active`]: batchActive },
            ]"
            :aria-label="actionBarAriaLabel"
          >
            <div :class="`${carbonPrefix}--action-list`">
              <slot name="batch-actions" />
              <cv-button
                :class="`${carbonPrefix}--batch-summary__cancel`"
                size="small"
                @click="deselect"
                >{{ batchCancelLabel }}</cv-button
              >
            </div>
            <div :class="`${carbonPrefix}--batch-summary`">
              <p :class="`${carbonPrefix}--batch-summary__para`">
                <span data-items-selected>
                  <slot
                    name="items-selected"
                    v-bind:scope="{ count: dataRowsSelected.length }"
                    >{{ dataRowsSelected.length }} items selected</slot
                  >
                </span>
              </p>
            </div>
          </div>

          <div :class="`${carbonPrefix}--toolbar-content`">
            <div
              v-if="$listeners.search"
              :class="{
                [`${carbonPrefix}--toolbar-search-container-active`]:
                  searchActive || searchValue.length > 0,
                [`${carbonPrefix}--toolbar-search-container-persistent`]:
                  !expandingSearch,
                [`${carbonPrefix}--toolbar-search-container-expandable`]:
                  expandingSearch,
              }"
              ref="searchContainer"
            >
              <div
                data-search
                :class="`${carbonPrefix}--search ${carbonPrefix}--search--sm`"
                role="search"
              >
                <div
                  :class="`${carbonPrefix}--search-magnifier`"
                  tabindex="0"
                  @click="checkSearchExpand(true)"
                  @keydown.enter.prevent="checkSearchExpand(true)"
                  @keydown.space.prevent
                  @keyup.space.prevent="checkSearchExpand(true)"
                  ref="magnifier"
                >
                  <Search16 :class="`${carbonPrefix}--toolbar-action__icon`" />
                </div>
                <label :for="uid" :class="`${carbonPrefix}--label`">{{
                  searchLabel
                }}</label>
                <input
                  :class="`${carbonPrefix}--search-input`"
                  type="text"
                  :id="uid"
                  role="search"
                  :placeholder="searchPlaceholder"
                  :aria-labelledby="uid"
                  ref="search"
                  v-model="searchValue"
                  @input="onSearch"
                  @keydown.esc.prevent.stop="checkSearchExpand(false)"
                />
                <button
                  :class="[
                    `${carbonPrefix}--search-close`,
                    {
                      [`${carbonPrefix}--search-close--hidden`]:
                        !clearSearchVisible,
                    },
                  ]"
                  :title="searchClearLabel"
                  :aria-label="searchClearLabel"
                  @click="onClearClick"
                  type="button"
                >
                  <Close16 />
                </button>
              </div>
            </div>
            <slot name="actions" />
          </div>
        </section>

        <div :class="`${carbonPrefix}--data-table-content`">
          <NsWrapper
            :tagType="stickyHeader ? section : ''"
            :class="`${carbonPrefix}--data-table_inner-container`"
          >
            <table
              :class="[
                `${carbonPrefix}--data-table`,
                {
                  [`${carbonPrefix}--data-table--${rowSize} `]: !(
                    rowSize.length === 0 || rowSize === 'standard'
                  ),
                  [`${carbonPrefix}--data-table--zebra `]: zebra,
                  [`${carbonPrefix}--data-table--sticky-header `]: stickyHeader,
                  [`${carbonPrefix}--data-table--no-border `]: borderless,
                  [`${carbonPrefix}--skeleton `]: skeleton,
                  [`${carbonPrefix}--data-table--sort `]: isSortable,
                  [`${carbonPrefix}--data-table--static `]: staticWidth,
                },
              ]"
            >
              <thead>
                <tr>
                  <th
                    v-if="hasExpandables"
                    :class="`${carbonPrefix}--table-expand`"
                    :data-previous-value="
                      dataExpandAll ? 'collapsed' : 'expanded'
                    "
                  >
                    <button
                      v-if="hasExpandAll"
                      :class="`${carbonPrefix}--table-expand__button`"
                      @click="toggleExpandAll"
                      type="button"
                      :aria-label="
                        dataExpandAll
                          ? collapseAllAriaLabel
                          : expandAllAriaLabel
                      "
                    >
                      <ChevronRight16
                        :class="`${carbonPrefix}--table-expand__svg`"
                      />
                    </button>
                  </th>
                  <th
                    v-if="hasBatchActions"
                    :class="`${carbonPrefix}--table-column-checkbox`"
                  >
                    <cv-checkbox
                      :form-item="false"
                      value="headingCheck"
                      v-model="headingChecked"
                      @change="onHeadingCheckChange"
                      :label="selectAllAriaLabel"
                      hideLabel
                    />
                  </th>
                  <slot name="headings">
                    <cv-data-table-heading
                      v-for="(column, index) in columns"
                      :key="`${index}:${column}`"
                      :heading="columnHeading(column)"
                      :sortable="isColSortable(column)"
                      :order="column.order"
                      :heading-style="headingStyle(column)"
                      :skeleton="skeleton"
                    />
                  </slot>
                  <th v-if="hasOverflowMenu"></th>
                </tr>
              </thead>

              <NsWrapper :tag-type="hasExpandables ? '' : 'tbody'">
                <slot name="data">
                  <cv-data-table-row
                    v-for="(row, rowIndex) in data"
                    :key="`row:${rowIndex}`"
                    :value="`${rowIndex}`"
                    ref="dataRows"
                    :overflow-menu="overflowMenu"
                  >
                    <cv-data-table-cell
                      v-for="(cell, colIndex) in row"
                      :key="`cell:${colIndex}:${rowIndex}`"
                      :style="dataStyle(colIndex)"
                    >
                      <NsWrapper :tag-type="skeleton ? 'span' : ''">{{
                        cell
                      }}</NsWrapper>
                    </cv-data-table-cell>
                  </cv-data-table-row>
                </slot>
              </NsWrapper>
            </table>
          </NsWrapper>
        </div>
      </div>
      <NsPagination
        v-if="newPagination"
        v-bind="internalPagination"
        :number-of-items="internalNumberOfItems"
        :actual-items-on-page="this.registeredRows.length"
        :pageSizesLabel="itemsPerPageLabel"
        :rangeOfTotalItemsLabel="rangeOfTotalItemsLabel"
        :ofTotalPagesLabel="ofTotalPagesLabel"
        :backwardText="backwardText"
        :forwardText="forwardText"
        :pageNumberLabel="pageNumberLabel"
        :page="pageNumber"
        @change="paginateTable($event)"
      >
        <template v-slot:range-text="{ scope }">
          <slot
            name="range-text"
            v-bind:scope="scope"
            v-if="$scopedSlots['range-text']"
          />
        </template>

        <template v-slot:of-n-pages="{ scope }">
          <slot
            name="of-n-pages"
            v-bind:scope="scope"
            v-if="$scopedSlots['of-n-pages']"
          ></slot>
        </template>
      </NsPagination>
    </div>
  </div>
</template>

<script>
import {
  CvDataTable,
  CvDataTableHeading,
  CvDataTableRow,
  CvDataTableCell,
  CvButton,
  CvCheckbox,
} from "@carbon/vue";
import NsWrapper from "./_ns-wrapper";
import NsPagination from "./NsPagination";
import Search16 from "@carbon/icons-vue/es/search/16";
import Close16 from "@carbon/icons-vue/es/close/16";
import ChevronRight16 from "@carbon/icons-vue/es/chevron--right/16";
import UtilService from "../lib-mixins/util.js";
import LottieService from "../lib-mixins/lottie.js";
import StorageService from "../lib-mixins/storage.js";

// localStorage entry holding the page sizes chosen by the user, grouped by
// page sizes set (e.g. {"10,25,50,100": 50}) or by pageSizeStorageKey prop
const PAGE_SIZES_STORAGE_KEY = "nsDataTablePageSizes";

export default {
  name: "NsDataTable",
  extends: CvDataTable,
  components: {
    CvButton,
    CvDataTableHeading,
    CvDataTableRow,
    CvDataTableCell,
    CvCheckbox,
    NsWrapper,
    Search16,
    Close16,
    ChevronRight16,
    NsPagination,
  },
  mixins: [UtilService, LottieService, StorageService],
  props: {
    actionBarAriaLabel: { type: String, default: "Table Action Bar" },
    collapseAllAriaLabel: { type: String, default: "Collapse all rows" },
    expandAllAriaLabel: { type: String, default: "Expand all rows" },
    selectAllAriaLabel: { type: String, default: "Select all rows" },
    autoWidth: Boolean,
    batchCancelLabel: { type: String, default: "cancel" },
    borderless: Boolean,
    overflowMenu: { type: [Boolean, Array], default: () => [] },
    pageSizes: {
      type: Array,
      default: () => [10, 25, 50, 100],
    },
    // remember the page size chosen by the user in localStorage
    persistPageSize: { type: Boolean, default: true },
    // key used to store the page size; tables with the same key share the same page size.
    // If empty, tables are grouped by their page sizes set
    pageSizeStorageKey: { type: String, default: "" },
    rowSize: {
      type: String,
      default: "standard",
      validator: (val) =>
        ["compact", "short", "standard", "tall", ""].includes(val),
    },
    searchLabel: { type: String, default: "Search" },
    searchPlaceholder: { type: String, default: "Search" },
    searchClearLabel: { type: String, default: "Clear search" },
    sortable: Boolean,
    title: String,
    columns: Array,
    data: Array,
    zebra: Boolean,
    stickyHeader: Boolean,
    rowsSelected: { type: Array, default: () => [] },
    helperText: { type: String, default: undefined },
    expandingSearch: { type: Boolean, default: true },
    skeleton: Boolean,
    hasExpandAll: Boolean,
    staticWidth: Boolean,
    // added
    allRows: { type: Array, default: () => [] },
    rawColumns: { type: Array, default: () => [] },
    isSearchable: { type: Boolean, default: false },
    isLoading: { type: Boolean, default: false },
    skeletonRows: { type: Number, default: 5 },
    isErrorShown: { type: Boolean, default: false },
    errorTitle: { type: String, default: "Cannot retrieve table data" },
    errorDescription: { type: String, default: "Something went wrong" },
    noSearchResultsLabel: { type: String, default: "No results" },
    noSearchResultsDescription: {
      type: String,
      default: "Try changing your search query",
    },
    filterRowsCallback: { type: Function },
    customSortTable: { type: Function },
    // default value of following props is defined in NsPagination
    itemsPerPageLabel: { type: String, default: undefined },
    rangeOfTotalItemsLabel: { type: String, default: undefined },
    ofTotalPagesLabel: { type: String, default: undefined },
    backwardText: { type: String, default: undefined },
    forwardText: { type: String, default: undefined },
    pageNumberLabel: { type: String, default: undefined },
  },
  data() {
    return {
      filteredRows: [],
      searchFilter: "",
      pageStart: 0,
      pageNumber: 0,
      pageLength: 0,
      selectedPageSize: null,
    };
  },
  watch: {
    allRows: function () {
      this.filterRows();
    },
    filteredRows: function () {
      this.$emit("updatePage", this.tablePage);
    },
    pageSizeGroup: function () {
      this.selectedPageSize = this.getStoredPageSize();
    },
  },
  created() {
    this.selectedPageSize = this.getStoredPageSize();
    this.filterRows();
  },
  computed: {
    newPagination() {
      if (this.pageSizes.length) {
        return {
          numberOfItems: this.filteredRows.length,
          pageSizes: this.paginationPageSizes,
        };
      } else {
        return false;
      }
    },
    isPageSizePersisted() {
      return (
        this.persistPageSize &&
        this.pageSizes.length > 1 &&
        this.pageSizes.every((size) => typeof size === "number")
      );
    },
    pageSizeGroup() {
      if (!this.isPageSizePersisted) {
        return "";
      }
      return this.pageSizeStorageKey || this.pageSizes.join(",");
    },
    paginationPageSizes() {
      if (
        this.selectedPageSize === null ||
        !this.pageSizes.includes(this.selectedPageSize)
      ) {
        return this.pageSizes;
      }
      // preselect page size in NsPagination
      return this.pageSizes.map((size) => ({
        value: size,
        selected: size === this.selectedPageSize,
      }));
    },
    tablePage() {
      if (this.pageSizes.length) {
        return this.filteredRows.slice(
          this.pageStart,
          this.pageStart + this.pageLength
        );
      } else {
        return this.filteredRows;
      }
    },
    internalPagination() {
      if (typeof this.newPagination === "object") {
        return this.newPagination;
      } else {
        if (this.newPagination === true) {
          return {};
        }
      }
      return false;
    },
  },
  methods: {
    onSort(srcComponent, val) {
      let index;
      for (let colIndex in this.registeredHeadings) {
        const column = this.registeredHeadings[colIndex];
        if (column.uid === srcComponent.uid) {
          column.internalOrder = val;
          index = colIndex;
        } else {
          column.internalOrder = "none";
        }
      }
      this.sortTable({ index, order: val });
    },
    onSearchInput() {
      // workaround to detect click on clear search button; search is handled by filterRows() with debounce
      if (!this.searchFilter) {
        this.filteredRows = this.allRows;
        this.goToFirstPage();
        this.focusElement("tableSearch");
      }
    },
    filterRows() {
      if (this.filterRowsCallback) {
        // call custom filterRows function
        this.filteredRows = this.filterRowsCallback(this.searchFilter);
      } else {
        this.filteredRows = this.defaultFilterRows();
      }
      this.goToFirstPage();
    },
    goToFirstPage() {
      if (this.pageNumber !== 1) {
        this.paginateTable({
          start: 1,
          page: 1,
          length: this.pageLength,
        });
      }
    },
    searchMatch(target, cleanRegex, queryText) {
      if (Array.isArray(target)) {
        // search field is an array (e.g. groups)
        return target.some((elem) => {
          return this.searchMatch(elem, cleanRegex, queryText);
        });
      } else if (typeof target === "string") {
        // search field is a simple string
        return new RegExp(queryText, "i").test(target.replace(cleanRegex, ""));
      } else if (typeof target === "number") {
        // search field is a number
        return new RegExp(queryText, "i").test(
          target.toString().replace(cleanRegex, "")
        );
      } else if (typeof target === "object") {
        // search field is an object, search in its attributes

        return Object.keys(target).some((key) => {
          // recursion
          return this.searchMatch(target[key], cleanRegex, queryText);
        });
      }
    },
    defaultFilterRows() {
      if (!this.searchFilter) {
        return this.allRows;
      } else {
        // clean query
        const cleanRegex = /[^a-zA-Z0-9]/g;
        const queryText = this.searchFilter.replace(cleanRegex, "");

        const searchResults = this.allRows.filter((option) => {
          // compare query text with attributes option
          return this.rawColumns.some((searchField) => {
            const target = option[searchField];

            if (target) {
              return this.searchMatch(target, cleanRegex, queryText);
            } else {
              return false;
            }
          });
        }, this);
        return searchResults;
      }
    },
    readStoredPageSizes() {
      try {
        const storedPageSizes = this.getFromStorage(PAGE_SIZES_STORAGE_KEY);

        if (
          storedPageSizes &&
          typeof storedPageSizes === "object" &&
          !Array.isArray(storedPageSizes)
        ) {
          return storedPageSizes;
        }
      } catch (e) {
        // corrupted value or storage not available
      }
      return {};
    },
    getStoredPageSize() {
      if (!this.pageSizeGroup) {
        return null;
      }
      const pageSize = this.readStoredPageSizes()[this.pageSizeGroup];

      if (this.pageSizes.includes(pageSize)) {
        return pageSize;
      }
      return null;
    },
    storePageSize(pageSize) {
      if (!this.pageSizeGroup) {
        return;
      }
      const storedPageSizes = this.readStoredPageSizes();
      storedPageSizes[this.pageSizeGroup] = pageSize;

      try {
        this.saveToStorage(PAGE_SIZES_STORAGE_KEY, storedPageSizes);
      } catch (e) {
        // storage not available or full
      }
    },
    paginateTable(ev) {
      if (
        this.isPageSizePersisted &&
        this.pageLength !== 0 &&
        ev.length !== this.pageLength
      ) {
        // page size changed by the user
        this.selectedPageSize = ev.length;
        this.storePageSize(ev.length);
      }
      this.pageStart = ev.start - 1;
      this.pageNumber = ev.page;
      this.pageLength = ev.length;
      this.$emit("updatePage", this.tablePage);
    },
    sortTable(ev) {
      const order = ev.order;

      if (order === "none") {
        return;
      }
      const propertyToSort = this.rawColumns[ev.index];

      if (this.customSortTable) {
        // call custom sort function
        this.filteredRows.sort(this.customSortTable(propertyToSort));
      } else {
        this.filteredRows.sort(this.sortByProperty(propertyToSort));
      }
      this.filteredRows.sort(this.sortByProperty(propertyToSort));

      if (ev.order === "descending") {
        this.filteredRows.reverse();
      }
      this.$emit("updatePage", this.tablePage);
    },
  },
};
</script>

<style scoped lang="scss">
// show data table pagination in smaller screens too
.cv-data-table
  ::v-deep
  .bx--pagination__left
  .cv-select.bx--form-item.bx--select__item-count {
  display: flex;
}

.cv-data-table ::v-deep .bx--pagination__right .bx--pagination__button {
  display: flex;
}

.cv-data-table ::v-deep .bx--pagination__right .bx--select__page-number {
  display: flex;
}

.cv-data-table ::v-deep .bx--pagination__right .bx--pagination__text {
  display: inline-block;
}
</style>
