import { createApp } from "vue";
import { createPinia } from "pinia";
import OrderApp from "./OrderApp.vue";
import "../styles/main.css";

createApp(OrderApp).use(createPinia()).mount("#app");
