export const SUPPORTED_FILE_TYPES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
  'text/markdown': ['.md', '.markdown'],
  'text/plain': ['.txt'],
};

export const SUPPORTED_EXTENSIONS = ['.pdf', '.docx', '.pptx', '.md', '.markdown', '.txt'];

export const ACCEPT_STRING = '.pdf,.docx,.pptx,.md,.markdown,.txt';

export const DEFAULT_SETTINGS = {
  llmProvider: 'anthropic',
  temperature: 0.2,
  maxTokens: 4096,
  showRAGPanel: true,
  username: 'default',
};

export const API_BASE = '';
