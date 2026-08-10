import { createRouter, createWebHashHistory } from "vue-router";
import Home from "./views/Home.vue";
import Shop from "./views/Shop.vue";
import Product from "./views/Product.vue";
import Cart from "./views/Cart.vue";
import About from "./views/About.vue";
import NotFound from "./views/NotFound.vue";

const router = createRouter({
  history: createWebHashHistory(import.meta.env.BASE_URL),
  scrollBehavior() {
    return { top: 0 };
  },
  routes: [
    { path: "/", name: "home", component: Home },
    { path: "/shop", name: "shop", component: Shop },
    { path: "/product/:id", name: "product", component: Product, props: true },
    { path: "/cart", name: "cart", component: Cart },
    { path: "/about", name: "about", component: About },
    { path: "/:pathMatch(.*)*", name: "not-found", component: NotFound },
  ],
});

export default router;
