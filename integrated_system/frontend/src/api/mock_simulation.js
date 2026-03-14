
export const mockBooks = [
    { id: 1, title: '遮天', author: '辰东', cover: '🐉' },
    { id: 2, title: '诡秘之主', author: '爱潜水的乌贼', cover: '🧐' },
    { id: 3, title: '凡人修仙传', author: '忘语', cover: '💊' }
]

export const mockReaderProfiles = [
    {
        id: 1,
        name: '毒舌书评人',
        username: 'BookWorm_99',
        avatar: '👨‍🏫',
        role: 'Critic',
        sentiment: -0.2,
        activity_level: 0.8,
        region: '上海',
        tags: ['逻辑控', '节奏大师'],
        bio: '专业书评人，喜欢深度世界观，痛恨逻辑漏洞。'
    },
    {
        id: 2,
        name: '铁杆死忠粉',
        username: 'LuminaLoverl',
        avatar: '👩‍🎤',
        role: 'Fan',
        sentiment: 0.9,
        activity_level: 0.95,
        region: '北京',
        tags: ['CP党', '周边收藏家'],
        bio: '沉迷角色关系，为了维护主角可以与全世界为敌。'
    },
    {
        id: 3,
        name: '数据考据党',
        username: 'Stats_Guru',
        avatar: '🤖',
        role: 'Researcher',
        sentiment: 0.1,
        activity_level: 0.4,
        region: '深圳',
        tags: ['战力崩坏监测', '经济系统'],
        bio: '专门分析魔法体系和经济系统的合理性，自带Excel看书。'
    },
    {
        id: 4,
        name: '路人读者',
        username: 'JustReadIt',
        avatar: '🚶',
        role: 'Reader',
        sentiment: 0.5,
        activity_level: 0.6,
        region: '广州',
        tags: ['找乐子', '跳过水文'],
        bio: '单纯为了打发时间，喜欢快节奏爽文，不爽就弃书。'
    },
    {
        id: 5,
        name: '资深老书虫',
        username: 'XianxiaMaster',
        avatar: '🧙‍♂️',
        role: 'Expert',
        sentiment: 0.3,
        activity_level: 0.7,
        region: '杭州',
        tags: ['套路百科', '纵向对比'],
        bio: '阅书过千的修仙大拿，喜欢把新书和经典神作做对比。'
    }
]

export const mockGraphDataMap = {
    1: { // 遮天
        nodes: [
            { uuid: 'n1', name: '叶凡 (主角)', labels: ['角色'] },
            { uuid: 'n2', name: '黑暗至尊', labels: ['角色'] },
            { uuid: 'n3', name: '万物母气鼎', labels: ['物品'] },
            { uuid: 'n4', name: '北斗星域', labels: ['地点'] },
            { uuid: 'n5', name: '荒古禁地', labels: ['地点'] },
            { uuid: 'n6', name: '姜太虚', labels: ['角色'] },
            { uuid: 'n7', name: '九秘', labels: ['功法'] }
        ],
        edges: [
            { source_node_uuid: 'n1', target_node_uuid: 'n3', name: '持有', fact_type: 'POSSESSION' },
            { source_node_uuid: 'n1', target_node_uuid: 'n2', name: '对决', fact_type: 'CONFLICT' },
            { source_node_uuid: 'n1', target_node_uuid: 'n6', name: '护道者', fact_type: 'RELATIONSHIP' },
            { source_node_uuid: 'n2', target_node_uuid: 'n5', name: '蛰伏于', fact_type: 'LOCATION' },
            { source_node_uuid: 'n4', target_node_uuid: 'n1', name: '降临地', fact_type: 'LOCATION' },
            { source_node_uuid: 'n6', target_node_uuid: 'n7', name: '传授', fact_type: 'ACTION' }
        ]
    },
    2: { // 诡秘之主
        nodes: [
            { uuid: 'k1', name: '克莱恩 (愚者)', labels: ['角色'] },
            { uuid: 'k2', name: '阿蒙', labels: ['角色'] },
            { uuid: 'k3', name: '源堡', labels: ['物品'] },
            { uuid: 'k4', name: '贝克兰德', labels: ['地点'] },
            { uuid: 'k5', name: '塔罗会', labels: ['组织'] },
            { uuid: 'k6', name: '正义小姐', labels: ['角色'] }
        ],
        edges: [
            { source_node_uuid: 'k1', target_node_uuid: 'k3', name: '执掌', fact_type: 'POSSESSION' },
            { source_node_uuid: 'k1', target_node_uuid: 'k2', name: '宿敌', fact_type: 'CONFLICT' },
            { source_node_uuid: 'k1', target_node_uuid: 'k5', name: '召集', fact_type: 'RELATIONSHIP' },
            { source_node_uuid: 'k6', target_node_uuid: 'k5', name: '成员', fact_type: 'RELATIONSHIP' },
            { source_node_uuid: 'k1', target_node_uuid: 'k6', name: '交易', fact_type: 'ACTION' },
            { source_node_uuid: 'k1', target_node_uuid: 'k4', name: '居住', fact_type: 'LOCATION' }
        ]
    },
    3: { // 凡人修仙传
        nodes: [
            { uuid: 'f1', name: '韩立 (韩跑跑)', labels: ['角色'] },
            { uuid: 'f2', name: '南宫婉', labels: ['角色'] },
            { uuid: 'f3', name: '掌天瓶', labels: ['物品'] },
            { uuid: 'f4', name: '乱星海', labels: ['地点'] },
            { uuid: 'f5', name: '青元剑诀', labels: ['功法'] }
        ],
        edges: [
            { source_node_uuid: 'f1', target_node_uuid: 'f3', name: '持有', fact_type: 'POSSESSION' },
            { source_node_uuid: 'f1', target_node_uuid: 'f2', name: '道侣', fact_type: 'RELATIONSHIP' },
            { source_node_uuid: 'f1', target_node_uuid: 'f4', name: '历练', fact_type: 'LOCATION' },
            { source_node_uuid: 'f1', target_node_uuid: 'f5', name: '修炼', fact_type: 'ACTION' }
        ]
    }
}

export const mockLiveFeedMap = {
    1: [ // 遮天
        { id: 101, agentId: 1, content: '第12章的节奏稍微有点赶，战力体系感觉要崩啊，作者注意一下。', time: '10:45 AM' },
        { id: 102, agentId: 2, content: '天哪！主角和女主的互动太甜了吧！我死了❤️❤️❤️', time: '10:46 AM' },
        { id: 103, agentId: 5, content: '虽然是标准的拍卖会套路，但是这一波装逼打脸处理得很清新脱俗。', time: '10:48 AM' }
    ],
    2: [ // 诡秘
        { id: 201, agentId: 3, content: '魔药序列的设定太严谨了，这才是真正的西幻！', time: '14:20 PM' },
        { id: 202, agentId: 1, content: '前面的铺垫有点长，主要是为了构建世界观，如果不喜欢的可能会觉得闷。', time: '14:25 PM' },
        { id: 203, agentId: 2, content: '赞美愚者！我要把这句话刻在DNA里！', time: '14:28 PM' }
    ],
    3: [ // 凡人
        { id: 301, agentId: 4, content: '这就是修仙界的黑暗森林法则吗？杀人夺宝太真实了。', time: '09:15 AM' },
        { id: 302, agentId: 1, content: '主角性格太稳健了，从来不浪，这点好评。', time: '09:30 AM' }
    ]
}

export const randomComments = [
    "刚刚更新的这一章太燃了！",
    "主角这个智商时刻在线，爱了爱了。",
    "作者短小无力，建议日更两万字。",
    "这个伏笔埋得好深，前面的坑终于填上了。",
    "反派死于话多，古人诚不欺我。",
    "这剧情走向完全没想到，神转折！",
    "能不能别再虐女主了，给寄刀片了啊！",
    "文笔稍微有点干，建议多描写一下环境。",
    "看到这里弃了，毒点太多。",
    "这就是我心目中的神作，预定年度最佳！"
]
