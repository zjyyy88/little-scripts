import argparse
import gc
from pathlib import Path

from bvlain import Lain


def parse_args():
    parser = argparse.ArgumentParser(
        description="Li-La-O 结构的 BVSE 计算脚本，包含自动氧化态检查回退。"
    )
    parser.add_argument(
        "--input",
        default=r"D:\my-post-graduate-life\third-year\田冰冰\tbb-LPSCI\tbb-LPSCI\Idoping\3.cif",
        help="输入结构文件，支持 cif/vasp 等格式。",
    )
    parser.add_argument("--mobile-ion", default="Li1+", help="迁移离子，默认 Li1+。")
    parser.add_argument("--r-cut", type=float, default=8.0, help="截断半径，默认 8.0。")
    parser.add_argument("--resolution", type=float, default=0.3, help="网格分辨率，默认 0.3。")
    parser.add_argument("--k", type=int, default=100, help="近邻搜索数量上限，默认 100。")
    parser.add_argument("--encut", type=float, default=5.0, help="渗流势垒能量截断，默认 5.0。")
    parser.add_argument(
        "--output-prefix",
        default=None,
        help=(
            "输出文件前缀，不需要写 .cube 后缀；"
            "默认写到当前工作目录，文件名为 <输入文件名>_bvse.cube。"
        ),
    )
    parser.add_argument(
        "--disable-oxi-check",
        action="store_true",
        help="关闭自动氧化态检查，等价于 read_file(..., oxi_check=False)。",
    )
    return parser.parse_args()


def read_structure_with_fallback(calc, structure_file, disable_oxi_check):
    if disable_oxi_check:
        calc.read_file(str(structure_file), oxi_check=False)
        print("已按 --disable-oxi-check 关闭自动氧化态检查。")
        return

    try:
        calc.read_file(str(structure_file), oxi_check=True)
    except Exception as exc:
        print(f"自动氧化态检查失败：{exc}")
        print("已自动回退为 oxi_check=False 继续计算。")
        calc.read_file(str(structure_file), oxi_check=False)


def resolve_output_prefix(input_path, output_prefix):
    if output_prefix:
        prefix_path = Path(output_prefix)
    else:
        prefix_path = Path.cwd() / f"{input_path.stem}_bvse"

    if prefix_path.suffix == ".cube":
        prefix_path = prefix_path.with_suffix("")

    prefix_path.parent.mkdir(parents=True, exist_ok=True)
    return prefix_path


def main():
    args = parse_args()
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在：{input_path}")

    output_prefix = resolve_output_prefix(input_path, args.output_prefix)

    calc = Lain(verbose=False)
    try:
        read_structure_with_fallback(calc, input_path, args.disable_oxi_check)

        params = {
            "mobile_ion": args.mobile_ion,
            "r_cut": args.r_cut,
            "resolution": args.resolution,
            "k": args.k,
        }

        calc.bvse_distribution(**params)
        energies = calc.percolation_barriers(encut=args.encut)

        print("\nPercolation barriers:")
        for key in energies:
            print(f"{key[-2:]} percolation barrier is {energies[key]:.4f} eV")

        calc.write_cube(str(output_prefix), task="bvse")
        print(f"\n已输出：{output_prefix}.cube")
    finally:
        del calc
        gc.collect()


if __name__ == "__main__":
    main()
