import React from 'react';
import { Card, CardContent, Typography, Box } from '@mui/material';

function NovelCard({ novel, index }) {
  const getGradeColor = (grade) => {
    switch(grade) {
      case 'S': return 'success';
      case 'A': return 'primary';
      case 'B': return 'warning';
      case 'C': return 'error';
      default: return 'default';
    }
  };

  return (
    <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography variant="h6" component="div" gutterBottom>
          {novel.title}
        </Typography>
        <Typography color="text.secondary" gutterBottom>
          作者: {novel.author || '未知'}
        </Typography>
        <Box sx={{ mb: 2 }}>
          <span style={{
            backgroundColor: getGradeColor(novel.Grade) === 'success' ? '#4caf50' : 
                           getGradeColor(novel.Grade) === 'primary' ? '#2196f3' :
                           getGradeColor(novel.Grade) === 'warning' ? '#ff9800' : '#f44336',
            color: 'white',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px',
            marginRight: '8px'
          }}>
            等级: {novel.Grade}
          </span>
          <span style={{
            border: '1px solid #ccc',
            padding: '4px 8px',
            borderRadius: '4px',
            fontSize: '12px'
          }}>
            IP值: {novel.IP_Value?.toFixed(1)}
          </span>
        </Box>
        <Typography variant="body2" color="text.secondary">
          字数: {(novel.word_count / 10000)?.toFixed(1)}万字
        </Typography>
        <Typography variant="body2" color="text.secondary">
          情感评分: {novel.sentiment_score?.toFixed(2)}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          分类: {novel.category || '未知'}
        </Typography>
      </CardContent>
    </Card>
  );
}

export default NovelCard;