<template>
  <div class="stat-card">
    <div class="icon-box">
      <el-icon :size="24"><component :is="icon" /></el-icon>
    </div>
    <div class="content">
      <div class="label">{{ title }}</div>
      <div class="value">
        {{ value }}
        <span v-if="suffix" class="suffix">{{ suffix }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: String,
  value: [Number, String],
  icon: String,
  suffix: String
})
</script>

<style scoped>
.stat-card {
  background: linear-gradient(135deg, rgba(76, 201, 240, 0.1), rgba(67, 97, 238, 0.1));
  border: 1px solid #4cc9f0;
  border-radius: 10px;
  padding: 15px 25px;
  display: flex;
  align-items: center;
  min-width: 200px;
  box-shadow: 0 0 10px rgba(76, 201, 240, 0.2);
}
.icon-box {
  width: 50px;
  height: 50px;
  background: rgba(76, 201, 240, 0.2);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 15px;
  color: #4cc9f0;
}
.label {
  font-size: 14px;
  color: #a0a0a0;
  margin-bottom: 5px;
}
.value {
  font-size: 24px;
  font-weight: bold;
  font-family: 'Courier New', Courier, monospace;
  color: #fff;
  text-shadow: 0 0 5px #4cc9f0;
}
.suffix {
  font-size: 14px;
  color: #a0a0a0;
  margin-left: 5px;
}
</style>
