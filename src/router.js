import { createRouter, createWebHashHistory } from "vue-router";
import Home from "./views/Home.vue";
import Shop from "./views/Shop.vue";
import Product from "./views/Product.vue";
import Cart from "./views/Cart.vue";
import About from "./views/About.vue";
import Contact from "./views/Contact.vue";
import Newsletter from "./views/Newsletter.vue";
import NotFound from "./views/NotFound.vue";

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
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

export default router;
