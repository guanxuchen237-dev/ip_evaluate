import React from 'react';
import { Grid } from '@mui/material';
import { Card, CardContent, Typography } from '@mui/material';

function StatsOverview({ stats }) {
  return (
    <Grid container spacing={3} sx={{ mb: 4 }}>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              总小说数
            </Typography>
            <Typography variant="h4">
              {stats.total_novels || 0}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              平均IP值
            </Typography>
            <Typography variant="h4">
              {stats.avg_ip_value || 0}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              主要题材
            </Typography>
            <Typography variant="body1">
              {Object.keys(stats.top_categories || {})[0] || '暂无'}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
      <Grid item xs={12} sm={6} md={3}>
        <Card>
          <CardContent>
            <Typography color="textSecondary" gutterBottom>
              S级作品数
            </Typography>
            <Typography variant="h4">
              {stats.grade_distribution?.S || 0}
            </Typography>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

export default StatsOverview;