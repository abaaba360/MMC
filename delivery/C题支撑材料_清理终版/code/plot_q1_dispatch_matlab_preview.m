%% 问题一：典型日功率调度与储能状态（国奖论文表达方式修订图）
% 输入：results/q1_detail.csv
% 输出：results/figures_matlab/q1_dispatch_matlab_awardstyle.{png,pdf,fig}
% 运行：matlab -batch "run('D:/数模工作流/code/plot_q1_dispatch_matlab_preview.m')"

clear; close all; clc;

rootDir = fileparts(fileparts(mfilename('fullpath')));
inputFile = fullfile(rootDir, 'results', 'q1_detail.csv');
outputDir = fullfile(rootDir, 'results', 'figures_matlab');
if ~exist(outputDir, 'dir')
    mkdir(outputDir);
end

T = readtable(inputFile, 'VariableNamingRule', 'preserve');
assert(height(T) == 144, '问题一明细应包含144个10分钟时段。');

% 附件首行“0:10”表示00:00—00:10时段的结束时刻；绘图采用时段中点。
t = (T.slot - 0.5) / 6;
kwFactor = 6;  % 10分钟电量(kWh)换算为该时段平均功率(kW)
loadKW = T.load_kwh * kwFactor;
pvKW = T.pv_kwh * kwFactor;
gridKW = T.grid_kwh * kwFactor;
chargeKW = T.charge_kwh * kwFactor;
dischargeKW = T.discharge_kwh * kwFactor;
socPct = 100 * T.soc_end_kwh / 12000;
price = T.price_yuan_per_kwh;

% 颜色采用低饱和、色盲相对友好的竞赛论文配色。
cNavy = [30, 78, 121] / 255;
cTeal = [42, 157, 143] / 255;
cGold = [233, 167, 55] / 255;
cCoral = [220, 92, 72] / 255;
cGray = [92, 102, 112] / 255;
cGrid = [220, 225, 230] / 255;

fig = figure('Color', 'w', 'Units', 'centimeters', ...
    'Position', [2, 2, 18.2, 14.8], 'Renderer', 'painters');
layout = tiledlayout(fig, 3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

% (a) 负荷、光伏与外网购电的时序关系。
ax1 = nexttile(layout, 1);
hold(ax1, 'on');
plot(ax1, t, loadKW, '-', 'Color', cNavy, 'LineWidth', 1.75);
plot(ax1, t, pvKW, '-', 'Color', cGold, 'LineWidth', 1.75);
stairs(ax1, t, gridKW, '--', 'Color', cTeal, 'LineWidth', 1.45);
ylabel(ax1, '功率 / kW');
legend(ax1, {'居民负荷', '光伏出力', '外网购电'}, ...
    'Location', 'northoutside', 'Orientation', 'horizontal', ...
    'Box', 'off', 'NumColumns', 3);
text(ax1, 0.01, 0.91, '(a)', 'Units', 'normalized', ...
    'FontName', 'Times New Roman', 'FontWeight', 'bold', 'FontSize', 10.5);

% (b) 储能动作：放电为正、充电为负；柱宽对应10分钟执行区间。
ax2 = nexttile(layout, 2);
hold(ax2, 'on');
hBar = bar(ax2, t, [dischargeKW, -chargeKW], 1.0, 'stacked', ...
    'EdgeColor', 'none');
hBar(1).FaceColor = cCoral;
hBar(1).FaceAlpha = 0.88;
hBar(2).FaceColor = cTeal;
hBar(2).FaceAlpha = 0.82;
yline(ax2, 0, '-', 'Color', cGray, 'LineWidth', 0.85);
ylabel(ax2, '储能功率 / kW');
legend(ax2, {'放电', '充电'}, 'Location', 'northoutside', ...
    'Orientation', 'horizontal', 'Box', 'off', 'NumColumns', 2);
text(ax2, 0.01, 0.91, '(b)', 'Units', 'normalized', ...
    'FontName', 'Times New Roman', 'FontWeight', 'bold', 'FontSize', 10.5);

% (c) SOC与分时电价共同解释充放电动作的经济原因。
ax3 = nexttile(layout, 3);
yyaxis(ax3, 'left');
plot(ax3, t, socPct, '-', 'Color', cNavy, 'LineWidth', 1.9);
yline(ax3, 10, ':', 'Color', cGray, 'LineWidth', 0.9);
yline(ax3, 90, ':', 'Color', cGray, 'LineWidth', 0.9);
ylabel(ax3, '储能荷电状态 SOC / %');
ylim(ax3, [5, 95]);

yyaxis(ax3, 'right');
stairs(ax3, t, price, '-', 'Color', cGold, 'LineWidth', 1.45);
ylabel(ax3, '电价 / (元·kWh^{-1})');
ax3.YAxis(1).Color = cGray;
ax3.YAxis(2).Color = cGray;
text(ax3, 0.01, 0.91, '(c)', 'Units', 'normalized', ...
    'FontName', 'Times New Roman', 'FontWeight', 'bold', 'FontSize', 10.5);

% 三个面板采用统一坐标和风格；图内不放总标题，标题交由论文题注。
axesList = [ax1, ax2, ax3];
for ax = axesList
    xlim(ax, [0, 24]);
    xticks(ax, 0:4:24);
    ax.FontName = 'Microsoft YaHei';
    ax.FontSize = 9.5;
    ax.LineWidth = 0.8;
    ax.TickDir = 'out';
    ax.Box = 'off';
    ax.XGrid = 'off';
    ax.YGrid = 'on';
    ax.GridColor = cGrid;
    ax.GridAlpha = 0.42;
    ax.MinorGridAlpha = 0.25;
end
ax1.XTickLabel = [];
ax2.XTickLabel = [];
xlabel(ax3, '时刻 / h');
linkaxes(axesList, 'x');

outBase = fullfile(outputDir, 'q1_dispatch_matlab_awardstyle');
exportgraphics(fig, [outBase '.png'], 'Resolution', 600, 'BackgroundColor', 'white');
exportgraphics(fig, [outBase '.pdf'], 'ContentType', 'vector', 'BackgroundColor', 'white');
savefig(fig, [outBase '.fig']);

fprintf('MATLAB图已生成：%s\n', outBase);
fprintf('数据范围：负荷 %.1f—%.1f kW，光伏 %.1f—%.1f kW，SOC %.1f%%—%.1f%%。\n', ...
    min(loadKW), max(loadKW), min(pvKW), max(pvKW), min(socPct), max(socPct));
