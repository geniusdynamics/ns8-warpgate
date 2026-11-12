<!--
  Copyright (C) 2024 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <div
    :class="[
      'combo-search-box',
      'cv-combo-box',
      `${carbonPrefix}--list-box__wrapper`,
      {
        [`${carbonPrefix}--text-input__field-wrapper--warning`]:
          !isInvalid && isWarn
      }
    ]"
    @focusout="onFocusOut"
  >
    <label
      v-if="title"
      :for="uid"
      :class="[
        `${carbonPrefix}--label`,
        { [`${carbonPrefix}--label--disabled`]: disabled }
      ]"
    >
      <div class="label-with-tooltip">
        <span>
          {{ title }}
        </span>
        <!-- tooltip -->
        <cv-interactive-tooltip
          v-if="hasTooltipSlot"
          :alignment="tooltipAlignment"
          :direction="tooltipDirection"
          class="info"
        >
          <template slot="content">
            <slot name="tooltip"></slot>
          </template>
        </cv-interactive-tooltip>
      </div>
    </label>

    <div
      role="listbox"
      tabindex="-1"
      class=""
      :class="[
        `${carbonPrefix}--combo-box ${carbonPrefix}--list-box`,
        {
          [`${carbonPrefix}--list-box--light`]: isLight,
          [`${carbonPrefix}--combo-box--expanded`]: open,
          [`${carbonPrefix}--list-box--expanded`]: open,
          [`${carbonPrefix}--combo-box--disabled ${carbonPrefix}--list-box--disabled`]:
            disabled
        }
      ]"
      :data-invalid="isInvalid"
      v-bind="$attrs"
      @keydown.down.prevent="onDown"
      @keydown.up.prevent="onUp"
      @keydown.enter.prevent="onEnter"
      @keydown.esc.prevent.stop="onEsc"
      @click="onClick"
    >
      <WarningFilled16
        v-if="isInvalid"
        :class="[`${carbonPrefix}--list-box__invalid-icon invalid-icon`]"
      />
      <WarningAltFilled16
        v-if="isWarn && !isInvalid"
        :class="`${carbonPrefix}--list-box__invalid-icon ${carbonPrefix}--list-box__invalid-icon--warning warn-icon`"
      />
      <div
        role="button"
        aria-haspopup="true"
        :aria-expanded="open ? 'true' : 'false'"
        :aria-owns="uid"
        :aria-controls="uid"
        :class="[`${carbonPrefix}--list-box__field`]"
        tabindex="-1"
        type="button"
        :aria-label="open ? 'close menu' : 'open menu'"
        data-toggle="true"
        ref="button"
      >
        <div :class="`${carbonPrefix}--search-magnifier`">
          <Search20 :class="`${carbonPrefix}--search-magnifier-icon`" />
        </div>
        <input
          ref="input"
          :class="[
            `${carbonPrefix}--text-input`,
            `${carbonPrefix}--search-input`,
            {
              [`${carbonPrefix}--text-input--empty`]:
                !filter || filter.length === 0
            }
          ]"
          :aria-controls="uid"
          aria-autocomplete="list"
          role="combobox"
          :aria-disabled="disabled"
          :aria-expanded="open ? 'true' : 'false'"
          autocomplete="off"
          :disabled="disabled"
          :placeholder="placeholder"
          v-model.trim="filter"
          v-debounce:500ms="performSearch"
          @input="onInput"
          @focus="inputFocus"
          @click.stop.prevent="inputClick"
        />
        <div
          v-if="filter"
          role="button"
          :class="[`${carbonPrefix}--list-box__selection`]"
          tabindex="0"
          :title="clearFilterLabel"
          @click.stop="clearFilter"
          @keydown.enter.stop.prevent="clearFilter"
          @keydown.space.stop.prevent
          @keyup.space.stop.prevent="clearFilter"
        >
          <Close16 />
        </div>

        <div :class="[`${carbonPrefix}--list-box__menu-icon`]" role="button">
          <chevron-down-16 :aria-label="open ? 'Close menu' : 'Open menu'" />
        </div>
      </div>

      <div
        v-show="open"
        :id="uid"
        :class="[`${carbonPrefix}--list-box__menu`]"
        role="listbox"
        ref="list"
      >
        <!-- loading results -->
        <div v-show="loadingResults">
          <cv-skeleton-text
            :paragraph="true"
            :line-count="4"
            class="loading-results"
          />
        </div>
        <!-- no results -->
        <div
          v-if="
            !loadingResults && !internalResults.length && noResults && filter
          "
        >
          <div :class="[`${carbonPrefix}--list-box__menu-item`]">
            <div
              :class="[
                `${carbonPrefix}--list-box__menu-item__option`,
                'item-disabled'
              ]"
            >
              {{ noResultsLabel }}
            </div>
          </div>
        </div>
        <div class="search-results">
          <!-- search results -->
          <div
            v-show="!loadingResults"
            v-for="(item, index) in limitedDataOptions"
            :key="`combo-box-${index}-${item.value}`"
            :class="[
              `${carbonPrefix}--list-box__menu-item`,
              {
                [`${carbonPrefix}--list-box__menu-item--highlighted`]:
                  highlighted === item.value
              }
            ]"
            ref="option"
            @click.stop.prevent="onItemClick(item.value)"
            @mousemove="onMousemove(item.value)"
            @mousedown.prevent
          >
            <div
              :class="[
                'search-result',
                `${carbonPrefix}--list-box__menu-item__option`
              ]"
            >
              {{ item.label }}
            </div>
          </div>
        </div>
        <!-- more results available -->
        <div
          v-if="
            !loadingResults &&
            internalResults.length &&
            (resultsLimitReached || internalResults.length > maxDisplayOptions)
          "
          :class="`${carbonPrefix}--list-box__menu-item`"
        >
          <div
            :class="[
              `${carbonPrefix}--list-box__menu-item__option`,
              'item-disabled'
            ]"
          >
            {{ resultsLimitReachedLabel }}
          </div>
        </div>
      </div>
    </div>
    <div v-if="isInvalid" :class="[`${carbonPrefix}--form-requirement`]">
      <slot name="invalid-message">{{ invalidMessage }}</slot>
    </div>
    <div
      v-if="isWarn && !isInvalid"
      :class="`${carbonPrefix}--form__requirement warn-text`"
    >
      <slot name="warn-text">{{ warnText }}</slot>
    </div>
    <div
      v-if="isHelper && !isInvalid && !isWarn"
      :class="[
        `${carbonPrefix}--form__helper-text`,
        { [`${carbonPrefix}--form__helper-text--disabled`]: disabled }
      ]"
    >
      <slot name="helper-text">{{ helperText }}</slot>
    </div>
  </div>
</template>

<script>
import {
  themeMixin,
  uidMixin,
  carbonPrefixMixin,
  methodsMixin
} from "@carbon/vue/src/mixins";
import WarningFilled16 from "@carbon/icons-vue/es/warning--filled/16";
import WarningAltFilled16 from "@carbon/icons-vue/es/warning--alt--filled/16";
import ChevronDown16 from "@carbon/icons-vue/es/chevron--down/16";
import Close16 from "@carbon/icons-vue/es/close/16";
import UtilService from "../lib-mixins/util.js";
import { mapState } from "vuex";
import Mark from "mark.js";
import Search20 from "@carbon/icons-vue/es/search/20";
import _cloneDeep from "lodash/cloneDeep";

export default {
  name: "NsComboSearchBox",
  inheritAttrs: false,
  mixins: [
    themeMixin,
    uidMixin,
    carbonPrefixMixin,
    methodsMixin({ input: ["focus", "blur"] }),
    UtilService
  ],
  components: {
    WarningFilled16,
    WarningAltFilled16,
    ChevronDown16,
    Close16,
    Search20
  },
  props: {
    results: { type: Array, default: () => [] },
    resultsLimitReached: { type: Boolean, default: false },
    loadingResults: { type: Boolean, default: false },
    autoHighlight: Boolean,
    disabled: Boolean,
    invalidMessage: { type: String, default: undefined },
    warnText: { type: String, default: undefined },
    helperText: { type: String, default: undefined },
    title: String,
    placeholder: {
      type: String,
      default: "Search"
    },
    highlight: String,
    value: String,
    clearFilterLabel: { type: String, default: "Clear search" },
    noResultsLabel: { type: String, default: "No results" },
    resultsLimitReachedLabel: {
      type: String,
      default: "Keep typing to show more options"
    },
    // limit the number of options to be displayed
    maxDisplayOptions: { type: Number, default: 100 },
    tooltipAlignment: {
      type: String,
      default: "start",
      validator: (val) => ["start", "center", "end"].includes(val)
    },
    tooltipDirection: {
      type: String,
      default: "bottom",
      validator: (val) => ["top", "left", "bottom", "right"].includes(val)
    }
  },
  data() {
    return {
      open: false,
      internalResults: [],
      lastQuery: "",
      dataValue: this.value,
      dataHighlighted: null,
      dataFilter: null,
      markInstance: null,
      isHelper: false,
      isInvalid: false,
      isWarn: false,
      noResults: false
    };
  },
  model: {
    prop: "value",
    event: "change"
  },
  watch: {
    highlight() {
      this.highlighted = this.highlight;
    },
    value() {
      this.dataValue = this.value;
      this.highlighted = this.value;
      this.internalUpdateValue(this.value);
    },
    results() {
      this.updateResults();
    },
    internalResults() {
      setTimeout(() => {
        // mark textQuery in internalResults
        const searchResults = document.querySelector(".search-results");
        this.markInstance = new Mark(searchResults);
        this.markInstance.mark(this.lastQuery.split(""), {
          className: "marked-bold"
        });
      }, 50);
    }
  },
  mounted() {
    this.filter = this.value;
    this.highlighted = this.value ? this.value : this.highlight; // override highlight with value if provided
    this.checkSlots();
    this.updateResults();
  },
  updated() {
    this.checkSlots();
  },
  computed: {
    ...mapState(["instanceName", "core"]),
    highlighted: {
      get() {
        return this.dataHighlighted;
      },
      set(val) {
        let firstMatchIndex = this.internalResults.findIndex(
          (item) => item.value === val
        );
        if (firstMatchIndex < 0) {
          firstMatchIndex = this.internalResults.length ? 0 : -1;
          this.dataHighlighted =
            firstMatchIndex >= 0 ? this.internalResults[0].value : "";
        } else {
          this.dataHighlighted = val;
        }
        if (firstMatchIndex >= 0) {
          this.$nextTick(() => {
            // $nextTick to prevent highlight check ahead of list update on filter
            this.checkHighlightPosition(firstMatchIndex);
          });
        }
      }
    },
    filter: {
      get() {
        return this.dataFilter;
      },
      set(val) {
        this.dataFilter = val ? val : "";
        this.$emit("filter", val);
      }
    },
    limitedDataOptions() {
      return this.internalResults.slice(0, this.maxDisplayOptions);
    },
    hasTooltipSlot() {
      return !!this.$slots.tooltip;
    }
  },
  methods: {
    checkSlots() {
      // NOTE: this.$slots is not reactive so needs to be managed on updated
      this.isInvalid = !!(
        this.$slots["invalid-message"] ||
        (this.invalidMessage && this.invalidMessage.length)
      );
      this.isHelper = !!(
        this.$slots["helper-text"] ||
        (this.helperText && this.helperText.length)
      );
      this.isWarn = !!(
        this.$slots["warn-text"] ||
        (this.warnText && this.warnText.length)
      );
    },
    clearFilter() {
      if (this.disabled) return;
      this.internalUpdateValue("");
      this.filter = "";
      this.internalResults = [];
      this.noResults = false;
      this.doOpen(false);
      this.$refs.input.focus();
      this.$emit("change", this.dataValue);
    },
    checkHighlightPosition(newHighlight) {
      if (
        this.$refs.list &&
        this.$refs.option &&
        this.$refs.option[newHighlight]
      ) {
        if (
          this.$refs.list.scrollTop > this.$refs.option[newHighlight].offsetTop
        ) {
          this.$refs.list.scrollTop = this.$refs.option[newHighlight].offsetTop;
        } else if (
          this.$refs.list.scrollTop + this.$refs.list.clientHeight <
          this.$refs.option[newHighlight].offsetTop +
            this.$refs.option[newHighlight].offsetHeight
        ) {
          this.$refs.list.scrollTop =
            this.$refs.option[newHighlight].offsetTop +
            this.$refs.option[newHighlight].offsetHeight -
            this.$refs.list.clientHeight;
        }
      }
    },
    doMove(up) {
      if (this.internalResults.length > 0) {
        // requery could have changed
        const currentHighlight = this.internalResults.findIndex(
          (item) => item.value === this.highlighted
        );
        let newHiglight;

        if (up) {
          if (currentHighlight <= 0) {
            newHiglight = this.internalResults.length - 1;
          } else {
            newHiglight = currentHighlight - 1;
          }
        } else {
          if (currentHighlight >= this.internalResults.length - 1) {
            newHiglight = 0;
          } else {
            newHiglight = currentHighlight + 1;
          }
        }
        this.highlighted = this.internalResults[newHiglight].value;
      }
    },
    updateHighlight() {
      let firstMatchIndex;
      if (this.autoHighlight && this.internalResults.length > 0) {
        // then highlight first match
        const filterRegex = new RegExp(this.filter, "iu");
        firstMatchIndex = this.internalResults.findIndex((item) =>
          filterRegex.test(item.label)
        );
        if (firstMatchIndex < 0) {
          firstMatchIndex = 0;
        }
        this.highlighted = this.internalResults[firstMatchIndex].value;
      }
    },
    onInput() {
      if (this.disabled) return;
      this.doOpen(true);
      this.noResults = false;
      this.updateHighlight();
    },
    doOpen(newVal) {
      this.open = newVal;
    },
    onDown() {
      if (this.disabled) return;
      if (!this.open) {
        this.doOpen(true);
      } else {
        this.doMove(false);
      }
    },
    onUp() {
      if (this.disabled) return;
      if (this.open) {
        this.doMove(true);
      }
    },
    onEsc() {
      if (this.disabled) return;
      this.doOpen(false);
      this.$el.focus();
    },
    onEnter() {
      if (this.disabled) return;
      this.doOpen(!this.open);
      if (!this.open) {
        this.onItemClick(this.highlighted);
        this.$refs.input.focus();
      }
    },
    onClick() {
      if (this.disabled) return;
      this.doOpen(!this.open);
      if (this.open) {
        this.$refs.input.focus();
      } else {
        this.$refs.button.focus();
      }
    },
    clearValues() {
      this.dataValue = "";
      this.$refs.input.focus();
      this.$emit("change", this.dataValue);
    },
    onFocusOut(ev) {
      if (!this.$el.contains(ev.relatedTarget)) {
        this.doOpen(false);
      }
    },
    onMousemove(val) {
      this.highlighted = val;
    },
    internalUpdateValue(val) {
      this.dataValue = val;
      const filterOption = this.internalResults.find(
        (item) => item.value === val
      );
      if (filterOption) {
        this.filter = filterOption.label;
      }
    },
    onItemClick(val) {
      if (!val) {
        return;
      }

      if (this.disabled) return;

      this.internalUpdateValue(val);
      this.$refs.input.focus();
      this.open = false; // close after user makes a selection
      this.$emit("change", this.dataValue);
    },
    inputClick() {
      if (this.disabled) return;

      if (!this.open) {
        this.doOpen(true);
      }
    },
    inputFocus() {
      if (this.disabled) return;
      this.doOpen(true);
    },
    updateResults() {
      this.internalResults = _cloneDeep(this.results);
      this.noResults = this.internalResults.length === 0;
    },
    performSearch(textQuery) {
      textQuery = textQuery.trim();

      if (textQuery === this.lastQuery) {
        return;
      }
      this.lastQuery = textQuery;

      if (!textQuery) {
        this.internalResults = [];
        return;
      }
      this.doOpen(true);

      // trigger search on parent component
      this.$emit("search", textQuery);
    }
  }
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tooltip";

.combo-search-box {
  max-width: none;
  position: relative;
}

.label-with-tooltip {
  display: flex;
  align-items: baseline;
}

.combo-search-box .warn-text {
  margin-top: 0.25rem;
}

.warn-icon,
.invalid-icon {
  right: 3rem;
}

.loading-results {
  padding: 2rem;
}
</style>

<style lang="scss">
// global styles

/* full width */
.combo-search-box .bx--text-input {
  max-width: none;
}

/* allow options with very long text to wrap on a new line */
.combo-search-box .bx--list-box__menu-item {
  height: auto;
}

/* allow options with very long text to wrap on a new line */
.combo-search-box .bx--list-box__menu-item__option {
  height: auto;
  text-overflow: clip;
  word-wrap: break-word;
  white-space: normal;
}

.combo-search-box .bx--list-box__menu-item__option.item-disabled {
  color: #a8a8a8;
  cursor: not-allowed;
}

.combo-search-box .bx--tooltip__label .bx--tooltip__trigger {
  margin-left: 0.25rem;
}

.combo-search-box .bx--list-box__invalid-icon--warning {
  position: absolute;
  top: 50%;
  right: 3rem;
  fill: #f1c21b;
  transform: translateY(-50%);
}

.combo-search-box
  .bx--list-box__invalid-icon--warning
  + .bx--list-box__field
  .bx--list-box__selection {
  right: 4rem !important;
}

.marked-bold {
  font-weight: bold;
  background-color: transparent;
}
</style>
