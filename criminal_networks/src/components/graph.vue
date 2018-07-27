<template lang='pug'>
div
  .box.content(ref='gbox')
    d3-network(:net-nodes='nodes',
      :options='options',
      :net-links='links'
      @node-click='nodeClick')
  nav.level.has-text-centered
    .level-item
      div
        .heading vertices
        .title {{ nNodes }}
    .level-item
      div
        .heading Edges
        .title {{ nLinks }}
  .title.is-size-4 Controls
  .field
    .control
      label.checkbox Show labels: 
        input(type='checkbox' @click="toggle('nodeLabels')")
  .field
    .control
      .file.has-name.is-left
        label.file-label
          input.file-input(type="file" name="resume")
          span.file-cta
            span.file-icon
              i.fas.fa-upload
            span.file-label Choose a file
          span.file-name filename
  .field
    .control
      a.button.is-info(@click='reset') Reset
  pre {{log}}
  pre(v-if='selected').
    Selected
    id: {{ selected.id }}
    name: {{ selected.name }}
    attributes: {{ selectedAttributes }}
  pre {{ statistics }}
</template>
  
<script>
import D3Network from 'vue-d3-network'
import options from './options'
import criminal from './criminal'
import { _ } from 'vue-underscore'
export default {
  data () {
    var d = Object.assign({}, options)
    d.nodeAttributes = criminal.node_attributes
    d.selected = null
    this.log = ''
    return d
  },
  computed: {
    selectedAttributes () { return this.selected ? this.nodeAttributes[this.selected.id - 1] : [] },
    nNodes () { return this.nodes.length },
    nLinks () { return this.links.length },
    statistics () {
      var nodeObjs = {}
      if (this.nodes === []) return { bar: {} }
      this.nodes.forEach(n => {
        nodeObjs[n.id] = n
        nodeObjs[n.id].links = []
      })
      // fill the links
      this.links.forEach(link => {
        nodeObjs[link.tid].links.push(link.sid)
        nodeObjs[link.sid].links.push(link.tid)
      })
      return {
        bar: _.countBy(_.keys(nodeObjs), n => nodeObjs[n].links.length)
      }
    },
  },
  mounted () {
    this.reset()
    this.options.size.w = this.$refs.gbox.clientWidth
    this.options.size.h = this.$refs.gbox.clientHeight
  },
  methods: {
    nodeClick (event, node) {
      // there seems to be an issue where the selected nodes color is not updating
      // i should just use the built in selected list prop
      this.log += '\nclicked on node ' + node.id
      if (this.selected) {
        this.log += '\nselected = ' + this.selected.id
        if (this.selected.id === node.id) {
          this.remove(node)
          this.selected = null
          return
        }
        this.selected._color = ''
      }
      this.selected = node
      node._color = 'be385d'
    },
    toggle (what) {
      this.options[what] = !this.options[what]
      this.options = Object.assign({}, this.options)
    },
    remove (node) {
      var id = node.id
      this.nodes = this.nodes.filter(x => x.id !== id)
      this.links = this.links.filter(link => !(link.sid === id || link.tid === id))
    },
    reset () {
      this.log = ''
      var n = Math.max(Math.max.apply(Math, criminal.ID1), Math.max.apply(Math, criminal.ID2))
      this.nodes = Array.apply(null, { length: n })
        .map((value, index) => {
          return { id: index + 1 }
        })
      this.links = criminal.ID1.map((s, index) => {
        return { tid: s, sid: criminal.ID2[index] }
      })
    }
  },
  components: { D3Network }
}
</script>
  
        
<style>
.selected {
  fill: #be385d;
  stroke-width: 5px;
}
</style>
  