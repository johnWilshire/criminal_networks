<template lang="pug">
#app
  section.hero
    .hero-body
      .container
        h1.title Criminal Network Analysis
        h2.subtitle sub title 
  .container
    graph
  br
  footer.footer
    .container
      .content.has-text-centered
        p Footer
        p citation lskjdljfsd slkjfds kdfsj 
</template>

<script>
import Graph from './components/graph.vue'

export default {
  name: 'app',
  components: { Graph }
}
</script>
<style src="vue-d3-network/dist/vue-d3-network.css"></style>
<style>

</style>
