/**
 * AI投资分析助手 - 图表绘制模块
 * 使用Chart.js绘制各种金融图表
 */

// 全局图表实例
let chartInstance = null;

// ========== 图表配置 ==========

const CHART_COLORS = {
    up: '#10b981',      // 涨 - 绿色
    down: '#ef4444',    // 跌 - 红色
    primary: '#2563eb', // 主色 - 蓝色
    secondary: '#8b5cf6', // 次要色 - 紫色
    neutral: '#6b7280', // 中性 - 灰色
    background: 'rgba(37, 99, 235, 0.1)', // 背景色
    grid: 'rgba(107, 114, 128, 0.1)'      // 网格线颜色
};

const CHART_OPTIONS = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        mode: 'index',
        intersect: false,
    },
    plugins: {
        legend: {
            display: true,
            position: 'top',
            labels: {
                usePointStyle: true,
                padding: 15,
                font: {
                    size: 12
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            padding: 12,
            titleFont: {
                size: 14,
                weight: 'bold'
            },
            bodyFont: {
                size: 13
            },
            cornerRadius: 8,
            displayColors: true
        }
    },
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                maxRotation: 45,
                minRotation: 0
            }
        },
        y: {
            grid: {
                color: CHART_COLORS.grid
            }
        }
    }
};

// ========== K线图 (蜡烛图) ==========

/**
 * 绘制K线图
 * @param {string} canvasId - Canvas元素ID
 * @param {Object} data - 股票数据
 * @param {string} title - 图表标题
 */
function drawCandlestickChart(canvasId, data, title = '股票K线图') {
    const canvas = $(canvasId);
    if (!canvas) return;

    // 销毁旧图表
    if (chartInstance) {
        chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');

    // 准备K线数据
    const candlestickData = {
        datasets: [{
            label: `${data.symbol} (${data.name})`,
            data: data.data.map(d => ({
                x: d.x,
                o: d.o,
                h: d.h,
                l: d.l,
                c: d.c
            })),
            borderColor: (context) => {
                const dataPoint = context.raw;
                return dataPoint.c >= dataPoint.o ? CHART_COLORS.up : CHART_COLORS.down;
            },
            backgroundColor: (context) => {
                const dataPoint = context.raw;
                const color = dataPoint.c >= dataPoint.o ? CHART_COLORS.up : CHART_COLORS.down;
                return color + '20'; // 添加透明度
            },
            borderWidth: 2,
            borderRadius: 4,
        }]
    };

    // 配置选项
    const options = {
        ...CHART_OPTIONS,
        plugins: {
            ...CHART_OPTIONS.plugins,
            title: {
                display: true,
                text: title,
                font: {
                    size: 16,
                    weight: 'bold'
                },
                padding: 20
            },
            legend: {
                display: false
            }
        },
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'day',
                    displayFormats: {
                        day: 'MM-DD'
                    }
                },
                grid: {
                    display: false
                }
            },
            y: {
                grid: {
                    color: CHART_COLORS.grid
                },
                ticks: {
                    callback: function(value) {
                        return '¥' + value.toFixed(2);
                    }
                }
            }
        }
    };

    try {
        chartInstance = new Chart(ctx, {
            type: 'bar',
            data: candlestickData,
            options: options
        });

        return chartInstance;
    } catch (error) {
        console.error('绘制K线图失败:', error);

        // 如果金融图表插件不可用，使用普通折线图
        return drawLineChart(canvasId, data, title);
    }
}

// ========== 折线图 ==========

/**
 * 绘制折线图
 * @param {string} canvasId - Canvas元素ID
 * @param {Object} data - 股票数据
 * @param {string} title - 图表标题
 */
function drawLineChart(canvasId, data, title = '股价走势图') {
    const canvas = $(canvasId);
    if (!canvas) return;

    if (chartInstance) {
        chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');

    // 准备折线数据
    const lineData = {
        labels: data.data.map(d => new Date(d.x).toLocaleDateString('zh-CN')),
        datasets: [{
            label: `${data.symbol} 收盘价`,
            data: data.data.map(d => d.c),
            borderColor: CHART_COLORS.primary,
            backgroundColor: CHART_COLORS.background,
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: CHART_COLORS.primary,
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2
        }]
    };

    const options = {
        ...CHART_OPTIONS,
        plugins: {
            ...CHART_OPTIONS.plugins,
            title: {
                display: true,
                text: title,
                font: {
                    size: 16,
                    weight: 'bold'
                },
                padding: 20
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                }
            },
            y: {
                grid: {
                    color: CHART_COLORS.grid
                },
                ticks: {
                    callback: function(value) {
                        return '¥' + value.toFixed(2);
                    }
                }
            }
        }
    };

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: lineData,
        options: options
    });

    return chartInstance;
}

// ========== 分时图 ==========

/**
 * 绘制分时图
 * @param {string} canvasId - Canvas元素ID
 * @param {Object} data - 分时数据
 * @param {string} title - 图表标题
 */
function drawTimeSeriesChart(canvasId, data, title = '分时图') {
    const canvas = $(canvasId);
    if (!canvas) return;

    if (chartInstance) {
        chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');

    const timeSeriesData = {
        labels: data.data.map(d => new Date(d.x).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit'
        })),
        datasets: [{
            label: '价格',
            data: data.data.map(d => d.c),
            borderColor: CHART_COLORS.primary,
            backgroundColor: (context) => {
                const ctx = context.chart.ctx;
                const gradient = ctx.createLinearGradient(0, 0, 0, 400);
                gradient.addColorStop(0, CHART_COLORS.primary + '40');
                gradient.addColorStop(1, CHART_COLORS.primary + '00');
                return gradient;
            },
            borderWidth: 2,
            fill: true,
            tension: 0.4,
            pointRadius: 0,
            pointHoverRadius: 6,
            pointHoverBackgroundColor: CHART_COLORS.primary,
            pointHoverBorderColor: '#fff',
            pointHoverBorderWidth: 2
        }]
    };

    const options = {
        ...CHART_OPTIONS,
        plugins: {
            ...CHART_OPTIONS.plugins,
            title: {
                display: true,
                text: title,
                font: {
                    size: 16,
                    weight: 'bold'
                }
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                },
                ticks: {
                    maxTicksLimit: 6
                }
            },
            y: {
                grid: {
                    color: CHART_COLORS.grid
                },
                ticks: {
                    callback: function(value) {
                        return value.toFixed(2);
                    }
                }
            }
        }
    };

    chartInstance = new Chart(ctx, {
        type: 'line',
        data: timeSeriesData,
        options: options
    });

    return chartInstance;
}

// ========== 柱状图 (成交量) ==========

/**
 * 绘制成交量柱状图
 * @param {string} canvasId - Canvas元素ID
 * @param {Object} data - 股票数据
 * @param {string} title - 图表标题
 */
function drawVolumeChart(canvasId, data, title = '成交量') {
    const canvas = $(canvasId);
    if (!canvas) return;

    if (chartInstance) {
        chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');

    // 判断涨跌
    const colors = data.data.map(d => {
        return d.c >= d.o ? CHART_COLORS.up : CHART_COLORS.down;
    });

    const volumeData = {
        labels: data.data.map(d => new Date(d.x).toLocaleDateString('zh-CN')),
        datasets: [{
            label: '成交量',
            data: data.data.map(d => d.v),
            backgroundColor: colors,
            borderColor: colors,
            borderWidth: 1,
            borderRadius: 2
        }]
    };

    const options = {
        ...CHART_OPTIONS,
        plugins: {
            ...CHART_OPTIONS.plugins,
            title: {
                display: true,
                text: title,
                font: {
                    size: 16,
                    weight: 'bold'
                }
            },
            legend: {
                display: false
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                }
            },
            y: {
                grid: {
                    color: CHART_COLORS.grid
                },
                ticks: {
                    callback: function(value) {
                        if (value >= 100000000) {
                            return (value / 100000000).toFixed(1) + '亿';
                        } else if (value >= 10000) {
                            return (value / 10000).toFixed(1) + '万';
                        }
                        return value;
                    }
                }
            }
        }
    };

    chartInstance = new Chart(ctx, {
        type: 'bar',
        data: volumeData,
        options: options
    });

    return chartInstance;
}

// ========== 组合图 (价格+成交量) ==========

/**
 * 绘制组合图
 * @param {string} canvasId - Canvas元素ID
 * @param {Object} data - 股票数据
 * @param {string} title - 图表标题
 */
function drawCombinedChart(canvasId, data, title = '股价分析') {
    const canvas = $(canvasId);
    if (!canvas) return;

    if (chartInstance) {
        chartInstance.destroy();
    }

    const ctx = canvas.getContext('2d');

    const combinedData = {
        labels: data.data.map(d => new Date(d.x).toLocaleDateString('zh-CN')),
        datasets: [
            {
                type: 'line',
                label: '收盘价',
                data: data.data.map(d => d.c),
                borderColor: CHART_COLORS.primary,
                backgroundColor: CHART_COLORS.background,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 0,
                yAxisID: 'y'
            },
            {
                type: 'bar',
                label: '成交量',
                data: data.data.map(d => d.v),
                backgroundColor: CHART_COLORS.secondary + '40',
                borderColor: CHART_COLORS.secondary,
                borderWidth: 1,
                yAxisID: 'y1'
            }
        ]
    };

    const options = {
        ...CHART_OPTIONS,
        plugins: {
            ...CHART_OPTIONS.plugins,
            title: {
                display: true,
                text: title,
                font: {
                    size: 16,
                    weight: 'bold'
                }
            }
        },
        scales: {
            x: {
                grid: {
                    display: false
                }
            },
            y: {
                type: 'linear',
                display: true,
                position: 'left',
                grid: {
                    color: CHART_COLORS.grid
                },
                ticks: {
                    callback: function(value) {
                        return '¥' + value.toFixed(2);
                    }
                }
            },
            y1: {
                type: 'linear',
                display: true,
                position: 'right',
                grid: {
                    drawOnChartArea: false
                },
                ticks: {
                    callback: function(value) {
                        if (value >= 100000000) {
                            return (value / 100000000).toFixed(1) + '亿';
                        } else if (value >= 10000) {
                            return (value / 10000).toFixed(1) + '万';
                        }
                        return value;
                    }
                }
            }
        }
    };

    chartInstance = new Chart(ctx, {
        data: combinedData,
        options: options
    });

    return chartInstance;
}

// ========== 模态框控制 ==========

/**
 * 显示图表模态框
 * @param {string} title - 标题
 */
function showChartModal(title = '股票图表') {
    const modal = $('chartModal');
    const titleElement = $('chartTitle');

    if (modal && titleElement) {
        titleElement.textContent = title;
        modal.classList.add('active');
    }
}

/**
 * 隐藏图表模态框
 */
function hideChartModal() {
    const modal = $('chartModal');
    if (modal) {
        modal.classList.remove('active');
    }
}

/**
 * 在模态框中显示图表
 * @param {Object} data - 股票数据
 * @param {string} chartType - 图表类型 ('candlestick', 'line', 'timeseries', 'volume', 'combined')
 */
function showChartInModal(data, chartType = 'combined') {
    const title = `${data.symbol} - ${data.name}`;

    switch (chartType) {
        case 'candlestick':
            drawCandlestickChart('stockChart', data, title);
            break;
        case 'line':
            drawLineChart('stockChart', data, title);
            break;
        case 'timeseries':
            drawTimeSeriesChart('stockChart', data, title);
            break;
        case 'volume':
            drawVolumeChart('stockChart', data, title);
            break;
        case 'combined':
        default:
            drawCombinedChart('stockChart', data, title);
            break;
    }

    showChartModal(title);
}

// ========== 事件监听 ==========

/**
 * 初始化图表模块
 */
function initChartModule() {
    // 关闭按钮事件
    const closeModalBtn = $('closeModal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', hideChartModal);
    }

    // 点击模态框外部关闭
    const modal = $('chartModal');
    if (modal) {
        modal.addEventListener('click', function(e) {
            if (e.target === modal) {
                hideChartModal();
            }
        });
    }

    // ESC键关闭
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hideChartModal();
        }
    });
}

// ========== 导出函数 ==========

window.drawCandlestickChart = drawCandlestickChart;
window.drawLineChart = drawLineChart;
window.drawTimeSeriesChart = drawTimeSeriesChart;
window.drawVolumeChart = drawVolumeChart;
window.drawCombinedChart = drawCombinedChart;
window.showChartModal = showChartModal;
window.hideChartModal = hideChartModal;
window.showChartInModal = showChartInModal;
window.initChartModule = initChartModule;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', initChartModule);
