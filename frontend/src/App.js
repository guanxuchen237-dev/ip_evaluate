import React from 'react';
import { Container, Typography, Box, Grid, Card, CardContent, TextField, Select, MenuItem, FormControl, InputLabel, Pagination } from '@mui/material';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import axios from 'axios';
import NovelCard from './components/NovelCard';
import StatsOverview from './components/StatsOverview';

function App() {
  const [novels, setNovels] = React.useState([]);
  const [stats, setStats] = React.useState({});
  const [visualizationData, setVisualizationData] = React.useState({});
  const [loading, setLoading] = React.useState(true);
  const [page, setPage] = React.useState(1);
  const [totalPages, setTotalPages] = React.useState(1);
  const [searchTerm, setSearchTerm] = React.useState('');
  const [categoryFilter, setCategoryFilter] = React.useState('');
  const [minScore, setMinScore] = React.useState('');
  const [sortBy, setSortBy] = React.useState('IP_Value');

  React.useEffect(() => {
    loadData();
  }, [page, searchTerm, categoryFilter, minScore, sortBy]);

  const loadData = async () => {
    try {
      setLoading(true);
      
      // Load novels with filters
      const novelsResponse = await axios.get('http://localhost:5000/api/novels', {
        params: {
          page,
          per_page: 12,
          category: categoryFilter,
          min_score: minScore,
          sort: sortBy
        }
      });
      
      setNovels(novelsResponse.data.novels);
      setTotalPages(Math.ceil(novelsResponse.data.total / 12));
      
      // Load stats
      const statsResponse = await axios.get('http://localhost:5000/api/stats');
      setStats(statsResponse.data);
      
      // Load visualization data
      const vizResponse = await axios.get('http://localhost:5000/api/visualization-data');
      setVisualizationData(vizResponse.data);
      
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handlePageChange = (event, value) => {
    setPage(value);
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8'];

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h3" component="h1" gutterBottom align="center">
          🌟 IP-Lumina 网络文学IP价值评估平台
        </Typography>
        <Typography variant="h6" color="text.secondary" align="center" sx={{ mb: 4 }}>
          基于数据挖掘的网络小说价值分析系统
        </Typography>

        {/* Stats Overview */}
        <StatsOverview stats={stats} />

        {/* Filters */}
        <Box sx={{ mb: 3, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <TextField
            label="搜索小说"
            variant="outlined"
            size="small"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            sx={{ minWidth: 200 }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>分类</InputLabel>
            <Select
              value={categoryFilter}
              label="分类"
              onChange={(e) => setCategoryFilter(e.target.value)}
            >
              <MenuItem value="">全部</MenuItem>
              {Object.keys(stats.top_categories || {}).map(cat => (
                <MenuItem key={cat} value={cat}>{cat}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="最低IP值"
            type="number"
            variant="outlined"
            size="small"
            value={minScore}
            onChange={(e) => setMinScore(e.target.value)}
            sx={{ minWidth: 120 }}
          />
          <FormControl size="small" sx={{ minWidth: 150 }}>
            <InputLabel>排序</InputLabel>
            <Select
              value={sortBy}
              label="排序"
              onChange={(e) => setSortBy(e.target.value)}
            >
              <MenuItem value="IP_Value">IP价值</MenuItem>
              <MenuItem value="word_count">字数</MenuItem>
              <MenuItem value="sentiment_score">情感评分</MenuItem>
            </Select>
          </FormControl>
        </Box>

        {/* Charts */}
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  IP价值TOP10
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={visualizationData.top10_ip || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="title" angle={-45} textAnchor="end" height={80} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="IP_Value" fill="#8884d8" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} md={6}>
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  等级分布
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={Object.entries(visualizationData.grade_dist || {}).map(([name, value]) => ({ name, value }))}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {Object.entries(visualizationData.grade_dist || {}).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </Grid>
        </Grid>

        {/* Novels Grid */}
        <Typography variant="h5" gutterBottom>
          小说列表 ({stats.total_novels || 0} 本)
        </Typography>
        
        {loading ? (
          <Typography>加载中...</Typography>
        ) : (
          <>
            <Grid container spacing={3}>
              {novels.map((novel, index) => (
                <Grid item xs={12} sm={6} md={4} key={index}>
                  <NovelCard novel={novel} index={index} />
                </Grid>
              ))}
            </Grid>
            
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Pagination 
                count={totalPages} 
                page={page} 
                onChange={handlePageChange} 
                color="primary" 
              />
            </Box>
          </>
        )}
      </Box>
    </Container>
  );
}

export default App;