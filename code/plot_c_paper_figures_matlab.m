%% C题论文问题二至问题四证据图（MATLAB统一重绘）
% 数据由 export_matlab_visual_data.py 从已验证结果导出；本脚本不重新求解模型。

clear; close all; clc;

rootDir = fileparts(fileparts(mfilename('fullpath')));
dataDir = fullfile(rootDir, 'results', 'matlab_plot_data');
outDir = fullfile(rootDir, 'results', 'figures_matlab');
if ~exist(outDir, 'dir'), mkdir(outDir); end

fontCN = 'Microsoft YaHei';
cNavy = [30, 78, 121] / 255;
cBlue = [76, 120, 168] / 255;
cTeal = [42, 157, 143] / 255;
cGold = [233, 167, 55] / 255;
cCoral = [220, 92, 72] / 255;
cPurple = [111, 78, 143] / 255;
cGray = [92, 102, 112] / 255;
cLight = [221, 227, 232] / 255;

%% 问题二：代表日计划误差与紧急购电
T = readtable(fullfile(dataDir, 'q2_representative_days.csv'), 'VariableNamingRule', 'preserve');
days = unique(string(T.date), 'stable');
fig = figure('Color','w','Units','centimeters','Position',[2 2 18.2 13.0],'Renderer','painters');
tl = tiledlayout(fig, 2, 2, 'TileSpacing','compact','Padding','compact');
for i = 1:numel(days)
    ax = nexttile(tl, i); hold(ax,'on');
    S = T(string(T.date)==days(i),:);
    b = bar(ax, S.hour, S.emergency_kw, 1.0, 'FaceColor',cCoral,'EdgeColor','none');
    b.FaceAlpha = 0.30;
    plot(ax, S.hour, S.actual_net_kw, '-', 'Color',cNavy,'LineWidth',1.55);
    plot(ax, S.hour, S.forecast_net_kw, '--', 'Color',cBlue,'LineWidth',1.25);
    text(ax,0.02,0.91,char(days(i)),'Units','normalized','FontName',fontCN,'FontWeight','bold','FontSize',9.2);
    styleAxes(ax,fontCN,cLight); xlim(ax,[0 24]); xticks(ax,0:6:24);
    if i > 2, xlabel(ax,'时刻 / h'); else, ax.XTickLabel=[]; end
    if mod(i,2)==1, ylabel(ax,'功率 / kW'); end
end
lg = legend(tl.Children(end), {'紧急购电','实际净负荷','日前点预测'}, ...
    'Orientation','horizontal','Box','off','NumColumns',3);
lg.Layout.Tile='north';
saveTriple(fig,outDir,'q2_representative_days_matlab'); close(fig);

%% 问题二：月度费用结构与紧急购电量
M = readtable(fullfile(dataDir, 'q2_monthly_summary.csv'), 'VariableNamingRule','preserve');
monthLabels = compose('%d月', month(datetime(M.date)));
x = 1:height(M);
fig = figure('Color','w','Units','centimeters','Position',[2 2 18.2 11.7],'Renderer','painters');
tl = tiledlayout(fig,2,1,'TileSpacing','compact','Padding','compact');
ax1 = nexttile(tl,1); hold(ax1,'on');
b = bar(ax1,x,[M.planned_cost_yuan M.emergency_cost_yuan]/1e4,'stacked','EdgeColor','none');
b(1).FaceColor=cBlue; b(2).FaceColor=cCoral;
ylabel(ax1,'月费用 / 万元');
legend(ax1,{'计划购电费','紧急购电费'},'Orientation','horizontal','Box','off','Location','northwest');
styleAxes(ax1,fontCN,cLight); ax1.XTick=[];
ax2 = nexttile(tl,2); hold(ax2,'on');
bar(ax2,x,M.emergency_energy_kwh/1e3,0.68,'FaceColor',cGold,'EdgeColor','none');
ylabel(ax2,'紧急购电量 / MWh'); xlabel(ax2,'月份');
xticks(ax2,x); xticklabels(ax2,monthLabels);
styleAxes(ax2,fontCN,cLight);
saveTriple(fig,outDir,'q2_monthly_cost_emergency_matlab'); close(fig);

%% 问题二：新增跨日SOC证据图
D = readtable(fullfile(dataDir, 'q2_daily_summary.csv'), 'VariableNamingRule','preserve');
dateNum = datetime(D.date);
fig = figure('Color','w','Units','centimeters','Position',[2 2 18.2 8.0],'Renderer','painters');
ax = axes(fig); hold(ax,'on');
xx = [dateNum; flipud(dateNum)];
yy = [D.soc_min_kwh; flipud(D.soc_max_kwh)]/12000*100;
fill(ax,xx,yy,cBlue,'FaceAlpha',0.16,'EdgeColor','none');
plot(ax,dateNum,D.soc_start_kwh/12000*100,'-','Color',cNavy,'LineWidth',1.05);
plot(ax,dateNum,D.soc_end_kwh/12000*100,'-','Color',cTeal,'LineWidth',0.95);
yline(ax,10,':','Color',cGray,'LineWidth',1.0);
yline(ax,90,':','Color',cGray,'LineWidth',1.0);
ylabel(ax,'储能荷电状态 SOC / %'); xlabel(ax,'日期'); ylim(ax,[5 95]);
legend(ax,{'日内SOC范围','每日0时SOC','每日24时SOC','运行边界'}, ...
    'Orientation','horizontal','Box','off','Location','northoutside','NumColumns',4);
styleAxes(ax,fontCN,cLight);
maxLink = max(abs(D.soc_link_residual_kwh));
text(ax,0.985,0.92,sprintf('跨日连接最大残差：%.1e kWh',maxLink), ...
    'Units','normalized','HorizontalAlignment','right','FontName',fontCN,'FontSize',8.5,'Color',cGray);
saveTriple(fig,outDir,'q2_soc_continuity_matlab'); close(fig);

%% 问题三：更新频率消融
A = readmatrix(fullfile(dataDir, 'q3_update_ablation.csv'), 'Delimiter', ',');
labels = {'仅0时','0/6时','0/6/12时','0/6/12/18时'};
x = 1:size(A,1);
fig = figure('Color','w','Units','centimeters','Position',[2 2 18.2 8.5],'Renderer','painters');
tl = tiledlayout(fig,1,2,'TileSpacing','compact','Padding','compact');
ax1 = nexttile(tl,1); hold(ax1,'on');
v1=A(:,1)/1e4;
bar(ax1,x,v1,0.64,'FaceColor',cBlue,'EdgeColor','none');
for i=1:numel(x), text(ax1,x(i),v1(i)+2.5,sprintf('%.1f',v1(i)),'HorizontalAlignment','center','FontSize',8.2); end
ylabel(ax1,'全年总费用 / 万元'); xticks(ax1,x); xticklabels(ax1,labels); xtickangle(ax1,16);
ylim(ax1,[min(v1)-18 max(v1)+18]); styleAxes(ax1,fontCN,cLight); text(ax1,0.02,0.94,'(a)','Units','normalized','FontWeight','bold');
ax2 = nexttile(tl,2); hold(ax2,'on');
v2=A(:,5)/1e3;
bar(ax2,x,v2,0.64,'FaceColor',cCoral,'EdgeColor','none');
for i=1:numel(x), text(ax2,x(i),v2(i)+8,sprintf('%.1f',v2(i)),'HorizontalAlignment','center','FontSize',8.2); end
ylabel(ax2,'紧急购电量 / MWh'); xticks(ax2,x); xticklabels(ax2,labels); xtickangle(ax2,16);
ylim(ax2,[0 max(v2)*1.14]); styleAxes(ax2,fontCN,cLight); text(ax2,0.02,0.94,'(b)','Units','normalized','FontWeight','bold');
saveTriple(fig,outDir,'q3_update_ablation_matlab'); close(fig);

%% 问题三：滚动预测修正轨迹
U = readtable(fullfile(dataDir, 'q3_representative_updates.csv'), 'VariableNamingRule','preserve');
days = unique(string(U.date),'stable');
fig = figure('Color','w','Units','centimeters','Position',[2 2 18.2 13.0],'Renderer','painters');
tl = tiledlayout(fig,2,2,'TileSpacing','compact','Padding','compact');
forecastNames={'forecast_00_kw','forecast_06_kw','forecast_12_kw','forecast_18_kw'};
forecastColors={cBlue,cTeal,cGold,cPurple};
for i=1:numel(days)
    ax=nexttile(tl,i); hold(ax,'on'); S=U(string(U.date)==days(i),:);
    b=bar(ax,S.hour,S.emergency_kw,1.0,'FaceColor',cCoral,'EdgeColor','none'); b.FaceAlpha=0.25;
    plot(ax,S.hour,S.actual_net_kw,'-','Color',cNavy,'LineWidth',1.6);
    for j=1:4
        plot(ax,S.hour,S.(forecastNames{j}),'--','Color',forecastColors{j},'LineWidth',1.0);
    end
    xline(ax,6,':','Color',cGray); xline(ax,12,':','Color',cGray); xline(ax,18,':','Color',cGray);
    text(ax,0.02,0.91,char(days(i)),'Units','normalized','FontName',fontCN,'FontWeight','bold','FontSize',9.2);
    styleAxes(ax,fontCN,cLight); xlim(ax,[0 24]); xticks(ax,0:6:24);
    if i>2, xlabel(ax,'时刻 / h'); else, ax.XTickLabel=[]; end
    if mod(i,2)==1, ylabel(ax,'功率 / kW'); end
end
lg=legend(tl.Children(end),{'紧急购电','实际净负荷','0时预测','6时预测','12时预测','18时预测'}, ...
    'Orientation','horizontal','Box','off','NumColumns',6); lg.Layout.Tile='north';
saveTriple(fig,outDir,'q3_forecast_updates_matlab'); close(fig);

%% 问题四：总成本层级与价格信息价值
V = readmatrix(fullfile(dataDir, 'q4_information_value.csv'), 'Delimiter', ',');
questionLabels = {'Q4-2','Q4-3'};
x=1:size(V,1);
fig = figure('Color','w','Units','centimeters','Position',[2 2 18.2 8.6],'Renderer','painters');
tl=tiledlayout(fig,1,2,'TileSpacing','compact','Padding','compact');
ax1=nexttile(tl,1); hold(ax1,'on');
vals=V(:,2:4)/1e4;
b=bar(ax1,x,vals,'grouped','EdgeColor','none'); b(1).FaceColor=cBlue; b(2).FaceColor=cGold; b(3).FaceColor=cGray;
ylabel(ax1,'全年总费用 / 万元'); xticks(ax1,x); xticklabels(ax1,questionLabels);
legend(ax1,{'因果在线','完全价格信息','全信息下界'},'Box','off','Location','northoutside','NumColumns',3);
styleAxes(ax1,fontCN,cLight); text(ax1,0.02,0.94,'(a)','Units','normalized','FontWeight','bold');
ax2=nexttile(tl,2); hold(ax2,'on');
gap=V(:,5)/1e4;
bar(ax2,x,gap,0.55,'FaceColor',cCoral,'EdgeColor','none');
for i=1:numel(x)
    text(ax2,x(i),gap(i)+0.35,sprintf('%.2f万元\n(%.3f%%)',gap(i),V(i,6)), ...
        'HorizontalAlignment','center','FontName',fontCN,'FontSize',8.8);
end
ylabel(ax2,'价格信息损失 / 万元'); xticks(ax2,x); xticklabels(ax2,questionLabels);
ylim(ax2,[0 max(gap)*1.30]); styleAxes(ax2,fontCN,cLight); text(ax2,0.02,0.94,'(b)','Units','normalized','FontWeight','bold');
saveTriple(fig,outDir,'q4_information_value_matlab'); close(fig);

fprintf('问题二至问题四 MATLAB 图已输出到：%s\n', outDir);

function styleAxes(ax,fontCN,cGrid)
    ax.FontName=fontCN; ax.FontSize=9.2; ax.LineWidth=0.8; ax.TickDir='out'; ax.Box='off';
    ax.XGrid='off'; ax.YGrid='on'; ax.GridColor=cGrid; ax.GridAlpha=0.46;
end

function saveTriple(fig,outDir,stem)
    base=fullfile(outDir,stem);
    exportgraphics(fig,[base '.png'],'Resolution',600,'BackgroundColor','white');
    exportgraphics(fig,[base '.pdf'],'ContentType','vector','BackgroundColor','white');
    savefig(fig,[base '.fig']);
end
