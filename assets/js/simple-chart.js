// Minimal Chart.js Alternative
class SimpleChart {
    constructor(ctx, config) {
        this.ctx = ctx;
        this.config = config;
        this.canvas = ctx.canvas;
        this.init();
    }

    init() {
        this.canvas.width = this.canvas.offsetWidth;
        this.canvas.height = this.canvas.offsetHeight;
        this.draw();
    }

    draw() {
        const { type, data, options } = this.config;
        
        if (type === 'doughnut') {
            this.drawDoughnut(data, options);
        } else if (type === 'line') {
            this.drawLine(data, options);
        } else if (type === 'bar') {
            this.drawBar(data, options);
        } else if (type === 'radar') {
            this.drawRadar(data, options);
        }
    }

    drawDoughnut(data, options) {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 20;
        const cutout = options.cutout ? parseFloat(options.cutout) / 100 : 0;
        const innerRadius = radius * cutout;

        let currentAngle = -Math.PI / 2;
        const total = data.datasets[0].data.reduce((sum, val) => sum + val, 0);

        data.datasets[0].data.forEach((value, index) => {
            const sliceAngle = (value / total) * Math.PI * 2;
            
            this.ctx.beginPath();
            this.ctx.arc(centerX, centerY, radius, currentAngle, currentAngle + sliceAngle);
            this.ctx.arc(centerX, centerY, innerRadius, currentAngle + sliceAngle, currentAngle, true);
            this.ctx.closePath();
            this.ctx.fillStyle = data.datasets[0].backgroundColor[index];
            this.ctx.fill();
            
            currentAngle += sliceAngle;
        });

        // Draw percentage text in center
        if (options.plugins?.title?.text) {
            this.ctx.fillStyle = '#2D2D2D';
            this.ctx.font = 'bold 24px Inter, sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.textBaseline = 'middle';
            this.ctx.fillText(options.plugins.title.text, centerX, centerY);
        }
    }

    drawLine(data, options) {
        const padding = 60;
        const chartWidth = this.canvas.width - padding * 2;
        const chartHeight = this.canvas.height - padding * 2;
        
        // Draw axes
        this.ctx.strokeStyle = '#E5E5E5';
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.moveTo(padding, padding);
        this.ctx.lineTo(padding, this.canvas.height - padding);
        this.ctx.lineTo(this.canvas.width - padding, this.canvas.height - padding);
        this.ctx.stroke();

        // Draw data lines
        data.datasets.forEach((dataset, datasetIndex) => {
            this.ctx.strokeStyle = dataset.borderColor;
            this.ctx.lineWidth = 2;
            this.ctx.beginPath();
            
            if (dataset.borderDash) {
                this.ctx.setLineDash(dataset.borderDash);
            } else {
                this.ctx.setLineDash([]);
            }

            dataset.data.forEach((value, index) => {
                const x = padding + (index / (dataset.data.length - 1)) * chartWidth;
                const y = this.canvas.height - padding - (value / 12) * chartHeight;
                
                if (index === 0) {
                    this.ctx.moveTo(x, y);
                } else {
                    this.ctx.lineTo(x, y);
                }
            });
            this.ctx.stroke();
        });

        // Draw labels
        this.ctx.fillStyle = '#666';
        this.ctx.font = '12px Inter, sans-serif';
        this.ctx.textAlign = 'center';
        data.labels.forEach((label, index) => {
            const x = padding + (index / (data.labels.length - 1)) * chartWidth;
            this.ctx.fillText(label, x, this.canvas.height - padding + 20);
        });
    }

    drawBar(data, options) {
        const padding = 60;
        const chartWidth = this.canvas.width - padding * 2;
        const chartHeight = this.canvas.height - padding * 2;
        
        if (options.indexAxis === 'y') {
            // Horizontal bar chart
            const barHeight = chartHeight / data.labels.length * 0.6;
            const barSpacing = chartHeight / data.labels.length;
            
            data.datasets.forEach((dataset, datasetIndex) => {
                dataset.data.forEach((value, index) => {
                    const y = padding + index * barSpacing + (barSpacing - barHeight) / 2;
                    const width = (value / Math.max(...dataset.data)) * chartWidth * 0.8;
                    
                    this.ctx.fillStyle = Array.isArray(dataset.backgroundColor) 
                        ? dataset.backgroundColor[index] 
                        : dataset.backgroundColor;
                    this.ctx.fillRect(padding, y, width, barHeight);
                });
            });
            
            // Labels
            this.ctx.fillStyle = '#666';
            this.ctx.font = '10px Inter, sans-serif';
            this.ctx.textAlign = 'right';
            data.labels.forEach((label, index) => {
                const y = padding + index * barSpacing + barSpacing / 2;
                const labelText = Array.isArray(label) ? label.join(' ') : label;
                this.ctx.fillText(labelText, padding - 10, y);
            });
        } else {
            // Vertical bar chart
            const barWidth = chartWidth / data.labels.length * 0.6;
            const barSpacing = chartWidth / data.labels.length;
            
            data.datasets.forEach((dataset, datasetIndex) => {
                dataset.data.forEach((value, index) => {
                    const x = padding + index * barSpacing + (barSpacing - barWidth) / 2;
                    const height = (value / 10) * chartHeight * 0.8;
                    
                    this.ctx.fillStyle = dataset.backgroundColor;
                    this.ctx.fillRect(x, this.canvas.height - padding - height, barWidth, height);
                });
            });
        }
    }

    drawRadar(data, options) {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 60;
        const sides = data.labels.length;
        
        // Draw radar grid
        this.ctx.strokeStyle = '#E5E5E5';
        this.ctx.lineWidth = 1;
        
        // Draw concentric polygons
        for (let level = 1; level <= 5; level++) {
            this.ctx.beginPath();
            for (let i = 0; i <= sides; i++) {
                const angle = (i * 2 * Math.PI) / sides - Math.PI / 2;
                const x = centerX + Math.cos(angle) * radius * (level / 5);
                const y = centerY + Math.sin(angle) * radius * (level / 5);
                
                if (i === 0) {
                    this.ctx.moveTo(x, y);
                } else {
                    this.ctx.lineTo(x, y);
                }
            }
            this.ctx.stroke();
        }
        
        // Draw axes
        for (let i = 0; i < sides; i++) {
            const angle = (i * 2 * Math.PI) / sides - Math.PI / 2;
            this.ctx.beginPath();
            this.ctx.moveTo(centerX, centerY);
            this.ctx.lineTo(
                centerX + Math.cos(angle) * radius,
                centerY + Math.sin(angle) * radius
            );
            this.ctx.stroke();
        }
        
        // Draw data
        const dataset = data.datasets[0];
        this.ctx.fillStyle = dataset.backgroundColor;
        this.ctx.strokeStyle = dataset.borderColor;
        this.ctx.lineWidth = 2;
        
        this.ctx.beginPath();
        dataset.data.forEach((value, index) => {
            const angle = (index * 2 * Math.PI) / sides - Math.PI / 2;
            const distance = (value / 10) * radius;
            const x = centerX + Math.cos(angle) * distance;
            const y = centerY + Math.sin(angle) * distance;
            
            if (index === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        });
        this.ctx.closePath();
        this.ctx.fill();
        this.ctx.stroke();
        
        // Draw labels
        this.ctx.fillStyle = '#666';
        this.ctx.font = '10px Inter, sans-serif';
        this.ctx.textAlign = 'center';
        data.labels.forEach((label, index) => {
            const angle = (index * 2 * Math.PI) / sides - Math.PI / 2;
            const labelRadius = radius + 20;
            const x = centerX + Math.cos(angle) * labelRadius;
            const y = centerY + Math.sin(angle) * labelRadius;
            
            const labelText = Array.isArray(label) ? label.join(' ') : label;
            this.ctx.fillText(labelText, x, y);
        });
    }
}

// Global Chart constructor for compatibility
window.Chart = SimpleChart;