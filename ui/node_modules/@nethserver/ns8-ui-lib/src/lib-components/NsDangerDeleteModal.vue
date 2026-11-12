<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <NsModal
    kind="danger"
    size="default"
    :visible="isShown"
    @modal-hidden="onModalHidden"
    @primary-click="confirmDelete"
    :primary-button-disabled="name !== userInput || loading"
  >
    <template slot="title">{{ title }}</template>
    <template slot="content">
      <NsInlineNotification
        v-if="isWarningShown"
        kind="warning"
        :title="warning"
        :showCloseButton="false"
      />
      <slot v-if="$slots.description" name="description"></slot>
      <div v-else>{{ description }}</div>
      <slot name="explanation"></slot>
      <div class="type-to-confirm">{{ typeToConfirmMessage }}</div>
      <cv-form @submit.prevent="confirmDelete">
        <cv-text-input
          v-model="userInput"
          class="confirm-input"
          ref="userInput"
        ></cv-text-input>
      </cv-form>
      <NsInlineNotification
        v-if="isErrorShown"
        kind="error"
        :title="errorTitle"
        :description="errorDescription"
        :showCloseButton="false"
      />
    </template>
    <template slot="secondary-button">{{ cancelLabel }}</template>
    <template slot="primary-button">{{ deleteLabel }}</template>
  </NsModal>
</template>

<script>
import UtilService from "../lib-mixins/util.js";
import NsInlineNotification from "./NsInlineNotification.vue";
import NsModal from "./NsModal.vue";

export default {
  name: "NsDangerDeleteModal",
  //component added for storybook to work
  components: { NsInlineNotification, NsModal },
  mixins: [UtilService],
  props: {
    isShown: {
      type: Boolean,
      default: true
    },
    name: {
      type: String,
      required: true
    },
    title: {
      type: String,
      default: "Confirm deletion"
    },
    warning: {
      type: String,
      default: "Please read carefully"
    },
    isWarningShown: {
      type: Boolean,
      default: true
    },
    description: {
      type: String,
      default:
        "Do you really want to delete this object? This action is irreversible"
    },
    typeToConfirm: {
      type: String,
      default: ""
    },
    cancelLabel: {
      type: String,
      default: "Cancel"
    },
    deleteLabel: {
      type: String,
      default: "I understand, delete"
    },
    isErrorShown: {
      type: Boolean,
      default: false
    },
    errorTitle: {
      type: String,
      default: ""
    },
    errorDescription: {
      type: String,
      default: ""
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      userInput: ""
    };
  },
  computed: {
    typeToConfirmMessage() {
      if (this.typeToConfirm) {
        return this.typeToConfirm;
      } else {
        return `Type '${this.name}' to confirm deletion`;
      }
    }
  },
  watch: {
    isShown: function () {
      if (this.isShown) {
        this.userInput = "";

        setTimeout(() => {
          this.focusElement("userInput");
        }, 300);
      }
    }
  },
  methods: {
    onModalHidden() {
      this.$emit("hide");
    },
    confirmDelete() {
      if (this.name == this.userInput) {
        this.$emit("confirmDelete");
      }
    }
  }
};
</script>

<style scoped lang="scss">
@import "../lib-styles/tokens";

.confirm-input {
  margin-bottom: $spacing-05;
}

.type-to-confirm {
  margin-top: 2rem;
}
</style>
