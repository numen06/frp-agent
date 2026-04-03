<template>
  <div ref="editorContainer" class="code-editor" :style="{ height: height }"></div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, shallowRef } from 'vue'
import { EditorView, keymap, lineNumbers, highlightActiveLine, highlightActiveLineGutter, drawSelection, rectangularSelection, highlightSpecialChars } from '@codemirror/view'
import { EditorState, Compartment } from '@codemirror/state'
import { defaultKeymap, history, historyKeymap, indentWithTab } from '@codemirror/commands'
import { syntaxHighlighting, defaultHighlightStyle, bracketMatching, foldGutter, indentOnInput, foldKeymap } from '@codemirror/language'
import { searchKeymap, highlightSelectionMatches } from '@codemirror/search'
import { closeBrackets, closeBracketsKeymap } from '@codemirror/autocomplete'
import { oneDark } from '@codemirror/theme-one-dark'
import { javascript } from '@codemirror/lang-javascript'

const props = defineProps({
  modelValue: { type: String, default: '' },
  language: { type: String, default: 'shell' },
  readonly: { type: Boolean, default: false },
  height: { type: String, default: '300px' },
  theme: { type: String, default: 'dark' },
  lineWrapping: { type: Boolean, default: false },
  placeholder: { type: String, default: '' },
  minimap: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'change', 'focus', 'blur'])

const editorContainer = ref(null)
const editorView = shallowRef(null)
const languageCompartment = new Compartment()
const readonlyCompartment = new Compartment()
const themeCompartment = new Compartment()
const lineWrappingCompartment = new Compartment()

const placeholderPlugin = EditorView.theme({
  '.cm-content': {
    '&:empty::before': {
      content: props.placeholder ? `"${props.placeholder}"` : 'none',
      color: '#64748b',
      fontStyle: 'italic',
      pointerEvents: 'none',
      position: 'absolute'
    }
  }
})

const customTheme = EditorView.theme({
  '&': {
    fontSize: '14px',
    borderRadius: '8px',
    overflow: 'hidden',
    border: '1px solid #e2e8f0'
  },
  '.cm-scroller': {
    fontFamily: '"JetBrains Mono", "Fira Code", "Source Code Pro", Consolas, monospace',
    overflow: 'auto'
  },
  '&.cm-focused': {
    outline: 'none',
    borderColor: '#4f46e5',
    boxShadow: '0 0 0 3px rgba(79, 70, 229, 0.1)'
  },
  '.cm-gutters': {
    backgroundColor: '#f8fafc',
    borderRight: '1px solid #e2e8f0',
    color: '#94a3b8'
  },
  '.cm-activeLineGutter': {
    backgroundColor: '#f1f5f9',
    color: '#475569'
  },
  '.cm-activeLine': {
    backgroundColor: '#f1f5f9'
  },
  '.cm-selectionMatch': {
    backgroundColor: '#fef08a40'
  },
  '.cm-cursor': {
    borderLeftColor: '#4f46e5',
    borderLeftWidth: '2px'
  }
})

const darkCustomTheme = EditorView.theme({
  '&': {
    fontSize: '14px',
    borderRadius: '8px',
    overflow: 'hidden',
    border: '1px solid #334155'
  },
  '.cm-scroller': {
    fontFamily: '"JetBrains Mono", "Fira Code", "Source Code Pro", Consolas, monospace',
    overflow: 'auto'
  },
  '&.cm-focused': {
    outline: 'none',
    borderColor: '#6366f1',
    boxShadow: '0 0 0 3px rgba(99, 102, 241, 0.2)'
  },
  '.cm-gutters': {
    backgroundColor: '#1e293b',
    borderRight: '1px solid #334155',
    color: '#64748b'
  },
  '.cm-activeLineGutter': {
    backgroundColor: '#334155',
    color: '#e2e8f0'
  },
  '.cm-activeLine': {
    backgroundColor: '#1e293b'
  },
  '.cm-selectionMatch': {
    backgroundColor: '#eab30830'
  },
  '.cm-cursor': {
    borderLeftColor: '#a5b4fc',
    borderLeftWidth: '2px'
  }
})

function getLanguageExtension(lang) {
  switch (lang) {
    case 'javascript':
    case 'js':
      return javascript()
    case 'yaml':
    case 'yml':
      return []
    default:
      return []
  }
}

function getThemeExtensions() {
  if (props.theme === 'dark') {
    return [oneDark, darkCustomTheme]
  }
  return [customTheme]
}

let updateFromExternal = false

function createState(doc) {
  return EditorState.create({
    doc: doc || '',
    extensions: [
      lineNumbers(),
      highlightActiveLine(),
      highlightActiveLineGutter(),
      highlightSpecialChars(),
      history(),
      foldGutter(),
      drawSelection(),
      indentOnInput(),
      bracketMatching(),
      closeBrackets(),
      rectangularSelection(),
      highlightSelectionMatches(),
      syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
      keymap.of([
        ...defaultKeymap,
        ...historyKeymap,
        ...closeBracketsKeymap,
        ...foldKeymap,
        ...searchKeymap,
        indentWithTab
      ]),
      languageCompartment.of(getLanguageExtension(props.language)),
      readonlyCompartment.of(EditorState.readOnly.of(props.readonly)),
      themeCompartment.of(getThemeExtensions()),
      lineWrappingCompartment.of(props.lineWrapping ? EditorView.lineWrapping : []),
      placeholderPlugin,
      EditorView.updateListener.of((update) => {
        if (update.docChanged && !updateFromExternal) {
          const value = update.state.doc.toString()
          emit('update:modelValue', value)
          emit('change', value)
        }
        if (update.focusChanged) {
          if (update.view.hasFocus) {
            emit('focus')
          } else {
            emit('blur')
          }
        }
      })
    ]
  })
}

onMounted(() => {
  if (editorContainer.value) {
    editorView.value = new EditorView({
      state: createState(props.modelValue),
      parent: editorContainer.value
    })
  }
})

watch(() => props.modelValue, (newVal) => {
  if (!editorView.value) return
  const currentVal = editorView.value.state.doc.toString()
  if (newVal !== currentVal) {
    updateFromExternal = true
    editorView.value.dispatch({
      changes: {
        from: 0,
        to: editorView.value.state.doc.length,
        insert: newVal || ''
      }
    })
    updateFromExternal = false
  }
})

watch(() => props.language, (newLang) => {
  if (editorView.value) {
    editorView.value.dispatch({
      effects: languageCompartment.reconfigure(getLanguageExtension(newLang))
    })
  }
})

watch(() => props.readonly, (newVal) => {
  if (editorView.value) {
    editorView.value.dispatch({
      effects: readonlyCompartment.reconfigure(EditorState.readOnly.of(newVal))
    })
  }
})

watch(() => props.theme, () => {
  if (editorView.value) {
    editorView.value.dispatch({
      effects: themeCompartment.reconfigure(getThemeExtensions())
    })
  }
})

watch(() => props.lineWrapping, (newVal) => {
  if (editorView.value) {
    editorView.value.dispatch({
      effects: lineWrappingCompartment.reconfigure(newVal ? EditorView.lineWrapping : [])
    })
  }
})

onBeforeUnmount(() => {
  if (editorView.value) {
    editorView.value.destroy()
  }
})

defineExpose({
  getEditor: () => editorView.value,
  focus: () => editorView.value?.focus()
})
</script>

<style scoped>
.code-editor {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.code-editor :deep(.cm-editor) {
  height: 100%;
}

.code-editor :deep(.cm-scroller) {
  padding: 8px 0;
}
</style>
