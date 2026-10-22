import { createRouter, createWebHistory } from "vue-router";
import Home from "./views/Home.vue";
import Shop from "./views/Shop.vue";
import Product from "./views/Product.vue";
import Cart from "./views/Cart.vue";
import About from "./views/About.vue";
import Contact from "./views/Contact.vue";
import Newsletter from "./views/Newsletter.vue";
import NotFound from "./views/NotFound.vue";

import {legacyStoreTarget} from './legacy-links.js';
const legacy = legacyStoreTarget(window.location.href);
if (legacy) window.history.replaceState(window.history.state, '', legacy);

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior() {
    return { top: 0 };
  },
  routes: [
    { path: "/", name: "home", component: Home },
    {
      path: "/shop", name: "shop", component: Shop,
      beforeEnter: to => to.query.cat === "pocket"
        ? { path: "/shop", query: { ...to.query, cat: "video" }, replace: true }
        : true,
    },
    { path: "/product/:id", name: "product", component: Product, props: true },
    { path: "/cart", name: "cart", component: Cart },
    { path: "/account", name: "account", component: () => import('./views/Account.vue') },
    { path: "/about", name: "about", component: About },
    { path: "/newsletter", name: "newsletter", component: Newsletter },
    { path: "/contact", name: "contact", component: Contact },
    { path: "/:pathMatch(.*)*", name: "not-found", component: NotFound },
  ],
});

// Draft and unlisted previews must survive navigation and a browser refresh.
router.beforeEach(to => {
  const current = new URLSearchParams(window.location.search);
  const sticky = {};
  for (const key of ['preview', 'category-preview']) {
    if (current.has(key) && to.query[key] === undefined) sticky[key] = current.get(key);
  }
  return Object.keys(sticky).length ? {path:to.path,query:{...to.query,...sticky},hash:to.hash,replace:true} : true;
});
// An old hash link clicked while already on the homepage may not reload JS.
window.addEventListener('hashchange', () => {
  const target = legacyStoreTarget(window.location.href);
  if (target) router.replace(target);
});

export default router;
