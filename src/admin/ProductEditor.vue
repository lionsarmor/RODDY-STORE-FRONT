<script setup>
import { computed, ref } from "vue";
import MediaEditor from "./MediaEditor.vue";
import ProductTags from "../components/ProductTags.vue";
import { specsToText, textToSpecs } from "./utils";
const props = defineProps({ product: Object, catalog: Object, library: Array });
defineEmits(["close", "duplicate", "delete", "media-busy"]);
const tab = ref("details");
const specs = computed({
  get: () => specsToText(props.product.specs),
  set: (value) => {
    props.product.specs = textToSpecs(value);
  },
});
const cover = computed({
  get: () => (props.product.coverImage ? [props.product.coverImage] : []),
  set: (value) => {
    props.product.coverImage = value[0] || "";
  },
});
function toggleTag(id) {
  const tags = props.product.tags;
  if (tags.includes(id)) tags.splice(tags.indexOf(id), 1);
  else {
    const conflict =
      id === "ai-assisted" ? "no-ai" : id === "no-ai" ? "ai-assisted" : null;
    if (conflict && tags.includes(conflict))
      tags.splice(tags.indexOf(conflict), 1);
    tags.push(id);
  }
}
</script>
<template>
  <section class="editor-panel">
    <div class="editor-heading">
      <div>
        <p class="eyebrow">{{ product.sku || "NEW PRODUCT" }}</p>
        <h2>{{ product.name || "Untitled product" }}</h2>
      </div>
      <button class="button small" @click="$emit('close')">Close ×</button>
    </div>
    <div
      class="editor-tabs"
      role="tablist"
      aria-label="Product editor sections"
    >
      <button
        v-for="t in ['details', 'images', 'pricing', 'links']"
        :key="t"
        role="tab"
        :aria-selected="tab === t"
        @click="tab = t"
      >
        {{ t === "links" ? "Links & downloads" : t }}
      </button>
    </div>
    <div v-if="tab === 'details'" class="editor-content">
      <div class="form-grid">
        <label class="full">Product name<input v-model="product.name" /></label
        ><label
          >Product ID<input v-model="product.id" pattern="[a-z0-9-]+" /><small
            >Keep stable after publishing; used in links and carts.</small
          ></label
        ><label>SKU<input v-model="product.sku" /></label
        ><label
          >Department<select v-model="product.category">
            <option v-for="c in catalog.categories" :key="c.id" :value="c.id">
              {{ c.name }}
            </option>
          </select></label
        ><label
          >Product type<select v-model="product.type">
            <option value="physical">Physical / shipped</option>
            <option value="digital">Digital / software</option>
          </select></label
        ><label class="full"
          >Short description<input
            v-model="product.shortDescription"
            maxlength="160"
          /><small>Shown on homepage and catalog cards.</small></label
        ><label class="full"
          >Full description<textarea
            v-model="product.description"
            rows="7"
          /></label
        ><label class="full"
          >Why we made it (optional)<textarea
            v-model="product.story"
            rows="5"
            placeholder="The idea, the constraints, and the reason this product exists."
          /><small
            >Shown as a maker's note on the full product page. Leave blank to
            omit.</small
          ></label
        ><label class="full"
          >Release / availability note<textarea
            v-model="product.releaseNote"
            rows="2"
          />
        </label>
      </div>
      <div class="field-heading">
        <h3>Product tags</h3>
        <span>Colors are managed in Tags</span>
      </div>
      <div class="tag-options">
        <button
          v-for="tag in catalog.tags"
          :key="tag.id"
          :aria-pressed="product.tags.includes(tag.id)"
          @click="toggleTag(tag.id)"
        >
          <span>{{ product.tags.includes(tag.id) ? "☑" : "□" }}</span
          ><ProductTags :ids="[tag.id]" :definitions="catalog.tags" />
        </button>
      </div>
      <label
        >Specifications<textarea
          :value="specs"
          rows="5"
          placeholder="Processor: ESP32-C3&#10;Charging: USB-C"
          @change="specs = $event.target.value"
        /><small
          >One specification per line, formatted Name: Value.</small
        ></label
      >
    </div>
    <div v-if="tab === 'images'" class="editor-content">
      <p class="help-copy">
        The at-a-glance cover is the single image shown on homepage and catalog
        cards. The gallery is shown on the full product page, in the order
        below.
      </p>
      <MediaEditor
        v-model="cover"
        single
        title="At-a-glance / cover image"
        :library="library"
        @busy="$emit('media-busy', $event)"
      />
      <MediaEditor
        v-model="product.images"
        title="Product page gallery"
        :library="library"
        @busy="$emit('media-busy', $event)"
      />
      <button
        v-if="product.images.length"
        class="button small"
        @click="product.coverImage = product.images[0]"
      >
        Use first gallery image as cover
      </button>
    </div>
    <div v-if="tab === 'pricing'" class="editor-content">
      <div class="form-grid">
        <label
          >Price (USD)<input
            v-model.number="product.price"
            type="number"
            min="0"
            step=".01" /></label
        ><label
          >Original / compare-at price<input
            v-model.number="product.compareAtPrice"
            type="number"
            min="0"
            step=".01"
          /><small>Zero disables the crossed-out sale price.</small></label
        ><label
          >Availability<select v-model="product.status">
            <option value="available">Available</option>
            <option value="coming-soon">Coming soon — cannot buy</option>
            <option value="sold-out">Sold out — cannot buy</option>
          </select></label
        ><label
          >Stock quantity<input
            v-model.number="product.stock"
            type="number"
            min="0"
            step="1"
            :disabled="!product.trackStock"
        /></label>
      </div>
      <label class="check"
        ><input v-model="product.pricePending" type="checkbox" />Pricing to be
        announced (hides price and prevents purchase)</label
      >
      <label class="check"
        ><input v-model="product.trackStock" type="checkbox" />Track stock (turn
        off for unlimited digital products)</label
      >
      <label class="check"
        ><input v-model="product.active" type="checkbox" />Visible in
        storefront</label
      >
      <label class="check"
        ><input v-model="product.featured" type="checkbox" />Featured in
        homepage lineup</label
      >
      <p class="help-copy">
        A FREE tag requires a price of $0. Coming-soon products stay visible but
        cannot be purchased. Stock is managed manually; reconcile paid orders in
        the Orders panel.
      </p>
    </div>
    <div v-if="tab === 'links'" class="editor-content">
      <label
        >Documentation / schematics URL<input
          v-model="product.documentationUrl"
          type="url"
          placeholder="https://example.com/project/docs"
        /><small
          >Links to manuals, schematics or repair information from the product's
          documentation section. Leave blank until available.</small
        ></label
      >
      <label
        >GitHub repository<input
          v-model="product.githubUrl"
          type="url"
          placeholder="https://github.com/yourname/project"
        /><small
          >Appears as an “Explore on GitHub” button beside the
          description.</small
        ></label
      >
      <label
        >Free download URL<input
          v-model="product.downloadUrl"
          type="url"
          placeholder="https://github.com/yourname/project/releases/latest"
        /><small
          >For an available $0 product with announced pricing, this becomes a
          direct “Free download” button. It bypasses checkout.</small
        ></label
      >
      <p class="notice">
        These links are public. Paid digital delivery should use a fulfillment
        service; do not put private paid-download URLs here.
      </p>
    </div>
    <div class="editor-footer">
      <span>Changes are part of your draft until published.</span>
      <div>
        <button class="button small" @click="$emit('duplicate')">
          Duplicate</button
        ><button class="button small danger" @click="$emit('delete')">
          Delete product
        </button>
      </div>
    </div>
  </section>
</template>
