/** 中国 SVG 底图共享元数据与投影工具：统一省份名称和经纬度坐标换算口径。 */

export const provinceNames: Readonly<Record<string, string>> = {
  anhui: "安徽省", beijing: "北京市", chongqing: "重庆市", fujian: "福建省", gansu: "甘肃省",
  guangdong: "广东省", "guangxi-zhuang": "广西壮族自治区", guizhou: "贵州省", hainan: "海南省",
  hebei: "河北省", heilongjiang: "黑龙江省", henan: "河南省", "hong-kong": "香港特别行政区",
  hubei: "湖北省", hunan: "湖南省", jiangsu: "江苏省", jiangxi: "江西省", jilin: "吉林省",
  liaoning: "辽宁省", macau: "澳门特别行政区", "nei-mongol": "内蒙古自治区",
  "ningxia-hui": "宁夏回族自治区", quinghai: "青海省", shaanxi: "陕西省", shandong: "山东省",
  shanghai: "上海市", shanxi: "山西省", sichuan: "四川省", tianjin: "天津市",
  "xinjiang-uygur": "新疆维吾尔自治区", xizang: "西藏自治区", yunnan: "云南省", zhejiang: "浙江省",
};

const mapLongitudeOffset = -975.007848;
const mapLongitudeScale = 13.038228;
const mapLatitudeOffset = 807.719623;
const mapMercatorScale = -735.840147;

/** 使用底图校准后的 Mercator 投影，将业务经纬度转换为共享 SVG 坐标。 */
export function projectMapCoordinates(longitude: number, latitude: number): { x: number; y: number } {
  const latitudeRadians = latitude * Math.PI / 180;
  const mercatorLatitude = Math.log(Math.tan(Math.PI / 4 + latitudeRadians / 2));
  return {
    x: mapLongitudeOffset + mapLongitudeScale * longitude,
    y: mapLatitudeOffset + mapMercatorScale * mercatorLatitude,
  };
}
