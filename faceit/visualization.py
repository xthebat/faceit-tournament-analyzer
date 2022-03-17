import pandas as pd


GRAPHIC_LINE_COLOR = "#ce5729"
GRID_LINE_COLOR = "#303030"
BACKGROUND_COLOR = "#1f1f1f"
AXIS_LINE_COLOR = "#666666"


def draw_faceit_score_history(df: pd.DataFrame, view_type: str = "index"):
    if view_type == "month":
        df = df.groupby(pd.Grouper(key="date", axis=0, freq='M')).mean()
        df["date"] = df.index
        x = "date"
        style = "o-"
    elif view_type == "date":
        x = "date"
        style = "-"
    elif view_type == "index":
        x = "index"
        style = "-"
    else:
        raise ValueError(f"view_type must be month, date or index, got {view_type}")

    plot = df.plot(x=x, y="elo", style=style, color=GRAPHIC_LINE_COLOR)
    plot.grid(color=GRID_LINE_COLOR, which='major', linestyle="-")
    plot.grid(color=GRID_LINE_COLOR, which='minor', linestyle="--")
    plot.set_facecolor(BACKGROUND_COLOR)
    plot.xaxis.label.set_color(AXIS_LINE_COLOR)
    plot.yaxis.label.set_color(AXIS_LINE_COLOR)
    plot.tick_params(axis='both', which='both', colors=AXIS_LINE_COLOR)
    plot.spines['left'].set_color(AXIS_LINE_COLOR)
    plot.spines['right'].set_color(AXIS_LINE_COLOR)
    plot.spines['bottom'].set_color(AXIS_LINE_COLOR)
    plot.spines['top'].set_color(AXIS_LINE_COLOR)
    figure = plot.get_figure()
    figure.set_facecolor(BACKGROUND_COLOR)
    return figure, plot
