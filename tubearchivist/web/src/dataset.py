"""analyze data sets from pg"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

from src.db import DatabaseConnect


COLORS = {
    "main-bg": "#00202f",
    "highlight-bg": "#00293b",
    "highlight-error": "#990202",
    "highlight-error-light": "#c44343",
    "highlight-bg-transparent": "#00293baf",
    "main-font": "#eeeeee",
    "accent-font-dark": "#259485",
    "accent-font-light": "#97d4c8",
}

mpl.rcParams["axes.facecolor"] = COLORS.get("highlight-bg")
mpl.rcParams["axes.titlecolor"] = COLORS.get("main-font")
mpl.rcParams["axes.titlesize"] = 20
mpl.rcParams["figure.facecolor"] = COLORS.get("main-bg")
mpl.rcParams["lines.linewidth"] = 2
mpl.rcParams["xtick.color"] = COLORS.get("main-font")
mpl.rcParams["xtick.labelcolor"] = COLORS.get("main-font")
mpl.rcParams["ytick.color"] = COLORS.get("main-font")
mpl.rcParams["ytick.labelcolor"] = COLORS.get("main-font")
mpl.rcParams["grid.color"] = COLORS.get("main-font")
mpl.rcParams["grid.linestyle"] = "--"
mpl.rcParams["grid.alpha"] = 0.5


class Pulls:
    """analyze docker pulls"""

    query_pulls = """
        SELECT time_stamp, pulls
        FROM ta_docker_stats
        WHERE time_stamp > 1646092800
        ORDER BY time_stamp DESC;
    """

    query_release = """
        SELECT time_stamp, release_version
        FROM ta_release
        WHERE time_stamp > 1646092800
        ORDER BY time_stamp;
    """

    def build_plots(self):
        """build plots from dataframe"""
        pull_rows = self.get_pull_rows()
        self.cumulative(pull_rows)
        self.weekly_bar(pull_rows)

    def get_pull_rows(self):
        """get rows from pg"""
        handler = DatabaseConnect()
        rows = handler.db_execute(self.query_pulls)
        handler.db_close()

        return rows

    def cumulative(self, rows):
        """build cumulative plot"""
        df = self._load_df(rows)
        release_rows = self._get_release_rows()
        self._plot_daily_total(df, release_rows)

    def _get_release_rows(self):
        """get release dates and versions"""
        handler = DatabaseConnect()
        rows = handler.db_execute(self.query_release)
        handler.db_close()

        return rows

    def _load_df(self, rows, resample="D"):
        """build dataframe from pull rows"""
        df = pd.DataFrame(rows)
        df["time_stamp"] = pd.to_datetime(df["time_stamp"], unit="s")
        df.set_index("time_stamp", inplace=True)

        return df.resample(resample).max()

    def _plot_daily_total(self, df, release_rows):
        """create daily total plot"""
        half_df = self._calc_half_df(df)
        plt.plot(df, color=COLORS.get("highlight-error"), zorder=3)
        self._add_releases(release_rows, half_df)
        plt.title("Cumulative Docker Pulls")
        plt.savefig("/data/plot-cumulative-docker.png", dpi=300)
        plt.figure()

    def _calc_half_df(self, df):
        """calc the middle of df height"""
        return (df["pulls"].max() - df["pulls"].min()) // 2 + df["pulls"].min()

    def _add_releases(self, release_rows, half_df):
        """add release vert line to plt"""
        version_colors = {
            "v0.2.2": COLORS.get("accent-font-light"),
            "v0.3.1": COLORS.get("accent-font-dark"),
            "v0.3.3": COLORS.get("accent-font-light"),
        }
        release = pd.DataFrame(release_rows)
        release["time_stamp"] = pd.to_datetime(release["time_stamp"], unit="s")

        for ind in release.index:
            label = release["release_version"][ind]
            x_axis = release["time_stamp"][ind]
            if (match := version_colors.get(label)) is None:
                match = COLORS.get("main-font")
                linewidth=0.5
            else:
                plt.text(
                    x=x_axis,
                    y=half_df,
                    s=label,
                    color="black",
                    rotation=90,
                    verticalalignment="center",
                    horizontalalignment="center",
                    bbox={"facecolor": match, "edgecolor": 'none'},
                )
                linewidth=1

            plt.axvline(
                x=x_axis,
                linestyle="--",
                color=match,
                linewidth=linewidth,
                zorder=2,
            )

    def weekly_bar(self, rows):
        """create weekly bar chart"""
        weekly = self._load_df(rows, resample="W")
        weekly_diff = weekly.diff().dropna().reset_index()
        col = [COLORS.get("accent-font-light") for i in weekly_diff["pulls"]]
        col[-1] = COLORS.get("highlight-error")

        plt.bar(
            weekly_diff["time_stamp"],
            weekly_diff["pulls"],
            width=3,
            color=col,
            zorder=1,
        )
        plt.grid(zorder=2, axis="y")
        plt.title("Weekly Docker Pulls")
        plt.savefig("/data/plot-weekly-docker.png", dpi=300)
        plt.figure()
        plt.close()


def run_chart_recreate():
    """function to call from scheduler"""
    Pulls().build_plots()
