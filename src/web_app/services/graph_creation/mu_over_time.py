# type: ignore
from bokeh.embed import components
from bokeh.io import curdoc
from bokeh.layouts import column
from bokeh.models import (
    ColumnDataSource,
    CustomJS,
    DataRange1d,
    HoverTool,
    RangeTool,
)
from bokeh.plotting import figure
import pandas as pd


def create_player_performance_graph(df: pd.DataFrame):
    df["date"] = pd.to_datetime(df["date"])

    # Create a ColumnDataSource from the DataFrame
    source = ColumnDataSource(df)

    # Determine the latest and earliest dates in the dataset
    latest_date = df["date"].max().to_pydatetime()
    earliest_date = df["date"].min().to_pydatetime()

    # Set the x_range to cover all data from the earliest to the latest date
    start_date = earliest_date  # Start from the earliest date in the dataset
    end_date = latest_date  # End at the latest date in the dataset
    # Main plot for μ and Confident μ with standard deviation
    p = figure(
        title="Expected Value (Player Strength Over Time)",
        x_axis_type="datetime",
        height=350,
        sizing_mode="stretch_width",
        toolbar_location=None,  # Hide toolbar
        x_range=(start_date, end_date),  # Set default x_range to latest 1.5 years
        y_range=DataRange1d(),  # Automatically adjust y_range based on visible data
    )

    # Line plot for μ (mu_after)
    mu_line = p.line(
        "date",
        "mu_after",
        source=source,
        line_width=2,
        color="blue",
        legend_label="\u00b5 (mu)",
    )

    # Shaded area for standard deviation
    p.varea(
        x="date",
        y1="mu_upper",
        y2="mu_lower",
        source=source,
        fill_alpha=0.2,
        color="blue",
    )

    # Line plot for Confident μ
    confident_mu_line = p.line(
        "date",
        "confident_mu",
        source=source,
        line_width=2,
        color="#38b2ac",
        legend_label="Confident \u00b5 (\u00b5 - 3 \u22c5 \u03c3)",
    )

    # Markers for Confident μ
    p.scatter(
        "date",
        "confident_mu",
        size=8,  # Size of the markers
        source=source,
        color="orange",
        legend_label="Match Day",
    )

    # HoverTool for μ
    hover_mu = HoverTool(
        tooltips=[
            ("\u00b5", "@mu_after{0.2f}"),
            ("\u03c3", "@sigma_after{0.2f}"),
        ],
        formatters={"@date": "datetime"},  # Apply datetime formatting to the date
        mode="vline",  # Tool works when hovering vertically
        renderers=[mu_line],  # Apply hover tool to the blue line
    )

    # HoverTool for Confident μ
    hover_confident_mu = HoverTool(
        tooltips=[
            ("Date", "@date{%F}"),  # Display date in YYYY-MM-DD format
            (
                "Confident \u00b5",
                "@confident_mu{0.2f}",
            ),
            (
                "\u00b5 gain",
                "@delta_mu{0.2f}",
            ),
            ("Global Match Nr", "@global_match_nr"),
        ],
        formatters={"@date": "datetime"},  # Apply datetime formatting to the date
        mode="vline",  # Tool works when hovering vertically
        renderers=[confident_mu_line],
    )

    p.add_tools(hover_mu, hover_confident_mu)

    p.legend.location = "bottom_left"
    p.legend.background_fill_alpha = 0.0
    p.legend.click_policy = "hide"  # Allow hiding lines by clicking legend

    # Create a second plot for the range tool
    select = figure(
        title="Select a Range",
        height=100,
        sizing_mode="stretch_width",
        y_range=p.y_range,  # Share the y-axis with the main plot
        x_axis_type="datetime",
        tools="",  # No tools on this plot
        toolbar_location=None,
    )

    # Add both graphs to the range tool plot
    select.line("date", "mu_after", source=source, color="blue")
    select.line("date", "confident_mu", source=source, color="green")

    # Add the range tool to the second plot
    range_tool = RangeTool(x_range=p.x_range)
    range_tool.overlay.fill_color = "navy"
    range_tool.overlay.fill_alpha = 0.2

    select.add_tools(range_tool)

    # Remove gridlines and minor elements from range tool plot for clarity
    select.ygrid.grid_line_color = None
    select.xaxis.axis_label = "Match Date"

    # Updated y-range callback with buffers based on sigma and fixed bottom buffer
    callback = CustomJS(
        args=dict(p=p, source=source),  # noqa: C408
        code="""
        const start = p.x_range.start;
        const end = p.x_range.end;
        const data = source.data;
        const dates = data['date'];
        const mu_after = data['mu_after'];
        const sigma_after = data['sigma_after'];  // Using sigma for top buffer
        const confident_mu = data['confident_mu'];
        let min_y = Infinity;
        let max_y = -Infinity;
        let found_data = false;

        // Loop through the dataset and check for data points within the selected range
        for (let i = 0; i < dates.length; i++) {
            if (dates[i] >= start && dates[i] <= end) {
                // Calculate top buffer using mu_after and sigma
                max_y = Math.max(max_y, mu_after[i] + sigma_after[i] + 0.5);
                // Use fixed buffer below confident_mu
                min_y = Math.min(min_y, confident_mu[i] - 1.5);
                found_data = true;
            }
        }

        if (found_data) {
            // Adjust y-axis based on visible data with the buffers
            p.y_range.start = min_y;
            p.y_range.end = max_y;
        } else {
            // If no data is found, maintain the previous y-range
            // to prevent the graph from disappearing
            const global_max_y = Math.max(...mu_after.map(
                (m, i) => m + sigma_after[i] + 0.5)
            );
            const global_min_y = Math.min(...confident_mu.map(m => m - 1.5));
            p.y_range.start = global_min_y;
            p.y_range.end = global_max_y;
        }
    """,
    )

    # Attach callback to both range change
    p.x_range.js_on_change("start", callback)
    p.x_range.js_on_change("end", callback)

    # Use DocumentReady event to trigger the callback on page load
    curdoc().js_on_event("document_ready", callback)

    # Combine the two plots into one layout
    layout = column(p, select, sizing_mode="stretch_width")

    return components(layout)
