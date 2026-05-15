---
name: Vue.js Framework
description: Build interactive user interfaces with Vue.js - components, state management, templates, composition API, lifecycle hooks, and reactive data binding
license: Apache-2.0
metadata:
  author: Vue.js Team
  version: 3.4
  tags: [vuejs, javascript, frontend, framework, reactive, components]
  platforms: [claude-code, cursor, windsurf, any]
  triggers:
    - Vue component
    - Vue template
    - Vue state
    - Create Vue app
    - Vue router
    - Vue composition API
    - Vuex store
    - Vue lifecycle
    - Vue reactive
    - Vue directive
  use_cases:
    - Build single-page applications
    - Create reusable components
    - Manage application state
    - Build progressive web apps
  estimated_time: 15-20 minutes
  complexity_level: intermediate
  prerequisites:
    - JavaScript fundamentals
    - HTML and CSS knowledge
    - Node.js and npm
  source_url: https://vuejs.org
  last_updated: "2025-01-15"
---

# Vue.js Framework

## Getting Started

Vue.js is a progressive JavaScript framework for building user interfaces with reactive data binding.

### Project Setup

Using Vite (recommended):

```bash
# Create new project
npm create vite@latest my-app -- --template vue

# Navigate and install
cd my-app
npm install

# Development server
npm run dev

# Build for production
npm run build
```

## Vue Components

Components are reusable UI elements with template, script, and style.

### Single File Components (.vue)

```vue
<template>
  <div class="counter">
    <p>Count: {{ count }}</p>
    <button @click="increment">Increment</button>
  </div>
</template>

<script>
import { ref } from 'vue';

export default {
  name: 'Counter',
  setup() {
    const count = ref(0);

    const increment = () => {
      count.value++;
    };

    return { count, increment };
  },
};
</script>

<style scoped>
.counter {
  padding: 20px;
  border: 1px solid #ccc;
}

button {
  margin-top: 10px;
}
</style>
```

## Composition API

Modern approach using functions instead of objects:

```vue
<template>
  <form @submit.prevent="handleSubmit">
    <input v-model="form.email" type="email" placeholder="Email" required />
    <input v-model="form.password" type="password" placeholder="Password" required />
    <button type="submit" :disabled="loading">{{ loading ? 'Logging in...' : 'Login' }}</button>
  </form>
</template>

<script setup>
import { ref } from 'vue';

const form = ref({
  email: '',
  password: '',
});

const loading = ref(false);

const handleSubmit = async () => {
  loading.value = true;
  try {
    const response = await fetch('/api/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form.value),
    });
    if (response.ok) {
      console.log('Login successful');
    }
  } catch (error) {
    console.error('Login failed', error);
  } finally {
    loading.value = false;
  }
};
</script>
```

## Reactive Data

Reactivity is the core feature of Vue:

```javascript
import { ref, computed, watch, reactive } from 'vue';

// ref for primitives
const count = ref(0);
count.value++; // Must use .value in script

// reactive for objects
const state = reactive({
  user: { name: 'John', age: 30 },
  items: [],
});

// computed for derived state
const userAge = computed(() => state.user.age);

// watch for side effects
watch(
  () => state.user.age,
  (newAge, oldAge) => {
    console.log(`Age changed from ${oldAge} to ${newAge}`);
  }
);

// watchers with options
watch(
  () => state.items,
  (newItems) => {
    console.log('Items changed', newItems);
  },
  { deep: true } // Watch nested properties
);
```

## Template Syntax

Vue templates support directives and expressions:

```vue
<template>
  <!-- Interpolation -->
  <h1>{{ message }}</h1>

  <!-- Binding -->
  <img :src="imageUrl" :alt="imageName" />
  <input :value="inputValue" @input="updateInput" />

  <!-- v-if / v-else -->
  <div v-if="isLoggedIn">Welcome!</div>
  <div v-else>Please log in</div>

  <!-- v-for -->
  <ul>
    <li v-for="item in items" :key="item.id">{{ item.name }}</li>
  </ul>

  <!-- v-show (toggle display) -->
  <div v-show="showDetails">Details here</div>

  <!-- Event handling -->
  <button @click="handleClick">Click me</button>
  <input @keyup.enter="submit" />

  <!-- Class binding -->
  <div :class="{ active: isActive, disabled: isDisabled }">Status</div>

  <!-- Style binding -->
  <div :style="{ color: activeColor, fontSize: fontSize + 'px' }">Styled</div>
</template>
```

## Component Props and Emit

Parent-child communication:

```vue
<!-- Parent Component -->
<template>
  <ChildComponent 
    :title="message" 
    @update-title="updateMessage"
  />
</template>

<script setup>
import { ref } from 'vue';
import ChildComponent from './Child.vue';

const message = ref('Hello');

const updateMessage = (newMessage) => {
  message.value = newMessage;
};
</script>

<!-- Child Component -->
<template>
  <div>
    <h1>{{ title }}</h1>
    <button @click="emitUpdate">Change Title</button>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
});

const emit = defineEmits(['update-title']);

const emitUpdate = () => {
  emit('update-title', 'New Title');
};
</script>
```

## Lifecycle Hooks

React to component stages:

```javascript
import { onMounted, onUpdated, onUnmounted, onBeforeMount } from 'vue';

export default {
  setup() {
    onBeforeMount(() => {
      console.log('Component is about to mount');
    });

    onMounted(() => {
      console.log('Component mounted');
      // Fetch data, set up timers
    });

    onUpdated(() => {
      console.log('Component updated');
    });

    onUnmounted(() => {
      console.log('Component unmounted');
      // Clean up timers, subscriptions
    });
  },
};
```

## Router (Vue Router)

Single-page application routing:

```javascript
// router.js
import { createRouter, createWebHistory } from 'vue-router';
import Home from './pages/Home.vue';
import About from './pages/About.vue';

const routes = [
  { path: '/', component: Home },
  { path: '/about', component: About },
  { path: '/user/:id', component: UserDetail },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
```

In template:

```vue
<template>
  <nav>
    <router-link to="/">Home</router-link>
    <router-link to="/about">About</router-link>
  </nav>
  <router-view />
</template>
```

## State Management (Pinia)

Global state management:

```javascript
// stores/counter.js
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export const useCounterStore = defineStore('counter', () => {
  const count = ref(0);

  const doubleCount = computed(() => count.value * 2);

  const increment = () => count.value++;
  const decrement = () => count.value--;

  return { count, doubleCount, increment, decrement };
});

// In component
<script setup>
import { useCounterStore } from '@/stores/counter';

const store = useCounterStore();
</script>

<template>
  <div>
    <p>Count: {{ store.count }}</p>
    <p>Double: {{ store.doubleCount }}</p>
    <button @click="store.increment">+</button>
  </div>
</template>
```

## Forms and Validation

Handle form input with validation:

```vue
<script setup>
import { ref } from 'vue';

const form = ref({
  name: '',
  email: '',
  message: '',
});

const errors = ref({});

const validateForm = () => {
  errors.value = {};
  if (!form.value.name) errors.value.name = 'Name is required';
  if (!form.value.email.includes('@')) errors.value.email = 'Valid email required';
  if (form.value.message.length < 10) errors.value.message = 'Message too short';
  return Object.keys(errors.value).length === 0;
};

const handleSubmit = () => {
  if (validateForm()) {
    console.log('Form submitted', form.value);
  }
};
</script>

<template>
  <form @submit.prevent="handleSubmit">
    <div>
      <input v-model="form.name" placeholder="Name" />
      <span v-if="errors.name" class="error">{{ errors.name }}</span>
    </div>
    <div>
      <input v-model="form.email" type="email" placeholder="Email" />
      <span v-if="errors.email" class="error">{{ errors.email }}</span>
    </div>
    <div>
      <textarea v-model="form.message" placeholder="Message"></textarea>
      <span v-if="errors.message" class="error">{{ errors.message }}</span>
    </div>
    <button type="submit">Send</button>
  </form>
</template>
```

## Best Practices

1. **Component organization** - Keep components focused and reusable
2. **Props validation** - Always validate props with types
3. **Composition API** - Prefer Composition API over Options API for new projects
4. **Lazy loading** - Split components for code optimization
5. **v-key** - Always use keys in v-for loops for proper updates
6. **Avoid mutation** - Keep state immutable
7. **Watch dependencies** - Clean up watchers in onUnmounted
8. **Template formatting** - Keep templates simple and readable
9. **Error handling** - Add try-catch in async operations
10. **Performance** - Use computed properties instead of methods for caching

---

Source: Vue.js Official Documentation (https://vuejs.org)
