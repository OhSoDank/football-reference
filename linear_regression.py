import json
import numpy as np
import os
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.metrics import r2_score
from sklearn.svm import SVR

pd.set_option('display.max_columns', None)
dir_path = os.path.dirname(os.path.realpath(__file__))


def regress(x_vars, y_var, filepath):
    """
    Perform a linear regression of the x variables against the y variables. Save to specified
    path.
    :param x_vars:
        Iterable of variable names to have as independent variables.
    :param y_var:
        The name of the dependent variable.
    :param filepath:
        The filepath to save the results to, in JSON format.
    """
    results = {}
    for pos in ["CB", "DL", "Edge", "LB", "OL", "RB", "S", "TE", "WR"]:
        df = pd.read_csv(os.path.join(dir_path, f"{pos}.csv"))
        smaller_is_better = ["40yd", "3Cone", "Shuttle", "Pick"]
        y_var = [y_var]
        # Standardise all variables first, and multiply variables where a smaller value is
        # better by minus 1.
        for col in x_vars + y_var:
            df[col] = (df[col] - df[col].mean()) / df[col].std()
            if col in smaller_is_better:
                df[col] = df[col] * -1
        # Split the data into test (55%) and train (45%) data
        msk = np.random.rand(len(df)) < 0.55
        train = df[msk]
        test = df[~msk]
        x_train = train[x_vars]
        y_train = train[y_var]
        x_test = test[x_vars].values
        y_test = test[y_var].values
        lr = Ridge()
        svr = SVR()
        lr_fit = lr.fit(x_train, y_train)
        svr.fit(x_train, y_train)
        lr_predictions = lr.predict(x_test)
        svr_predictions = svr.predict(x_test)
        lr_r2_score = r2_score([el[0] for el in y_test], lr_predictions)
        svr_r2_score = r2_score([el[0] for el in y_test], svr_predictions)
        results[pos] = {"lr_r2_score": lr_r2_score,
                        "svr_r2_score": svr_r2_score,
                        "lr_coef": lr_fit.coef_.tolist(),
                        "lr_int": int(lr_fit.intercept_)}

    with open(filepath, "w") as json_f:
        json.dump(results, json_f)


regress(["Wt", "40yd", "Vertical", "Broad Jump", "3Cone", "Shuttle", "Height (cm)", "Pick"],
        "5AV", os.path.join(dir_path, "results", "results.json"))
regress(["Pick"], "5AV", os.path.join(dir_path, "results", "just_pick.json"))
regress(["Wt", "40yd", "Vertical", "Broad Jump", "3Cone", "Shuttle", "Height (cm)"], "Pick",
        os.path.join(dir_path, "results", "results.json"))
