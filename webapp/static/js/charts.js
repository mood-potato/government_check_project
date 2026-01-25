// Chart rendering utilities for Plotly.js

const ChartUtils = {
    // Common Plotly layout config for Korean
    baseLayout: {
        font: { family: 'Pretendard, system-ui, sans-serif' },
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        margin: { l: 100, r: 20, t: 20, b: 40 }
    },

    // Horizontal bar chart (speaker distribution)
    horizontalBar(containerId, labels, values, title) {
        const data = [{
            type: 'bar',
            x: values,
            y: labels,
            orientation: 'h',
            marker: { color: '#3b82f6' }
        }];

        const layout = {
            ...this.baseLayout,
            title: title ? { text: title, font: { size: 14 } } : null,
            xaxis: { title: '' },
            yaxis: { automargin: true }
        };

        Plotly.newPlot(containerId, data, layout, { responsive: true });
    },

    // Line chart (activity timeline)
    lineChart(containerId, dates, values, title) {
        const data = [{
            type: 'scatter',
            mode: 'lines+markers',
            x: dates,
            y: values,
            line: { color: '#3b82f6', width: 2 },
            marker: { size: 6 }
        }];

        const layout = {
            ...this.baseLayout,
            title: title ? { text: title, font: { size: 14 } } : null,
            xaxis: { title: '' },
            yaxis: { title: '' }
        };

        Plotly.newPlot(containerId, data, layout, { responsive: true });
    }
};
