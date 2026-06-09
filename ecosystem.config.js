module.exports = {
  apps: [{
    name: 'linkedin-autoapply',
    script: 'main.py',
    args: '--loop',
    interpreter: '/root/linkedin-autoapply/venv/bin/python3',
    cwd: '/root/linkedin-autoapply',
    max_memory_restart: '700M',
    autorestart: true,
  }]
}
