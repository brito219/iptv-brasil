# IPTV Brasil 🇧🇷

Lista M3U curada de canais de TV brasileiros, **testada automaticamente**: só entram canais que estão no ar no momento da geração.

-  Apenas canais do Brasil
-  Testado — streams fora do ar são removidos
-  Fontes: [iptv-org](https://github.com/iptv-org/iptv), [Pluto TV Brasil](https://pluto.tv/br) e streams oficiais de emissoras

## Como usar

Cole a URL abaixo no seu player (Jellyfin, VLC, Kodi, TiviMate, IPTV Smarters...):

```
https://raw.githubusercontent.com/brito219/iptv-brasil/main/brasil.m3u
```

### Jellyfin

Painel → TV ao Vivo → Sintonizadores → Adicionar → tipo **M3U** → cole a URL acima.

## Como funciona

- `curate.py` baixa as fontes, testa cada stream com ffprobe, filtra os que tocam de verdade e gera `brasil.m3u`.
- `essenciais.m3u` é uma lista fixa de streams oficiais de emissoras (TV Brasil, TV Cultura, afiliadas...).
- A geração roda num cron no homelab do autor a cada 2 dias e faz push pra cá.
- `channels.py` gera o `channels.xml` (mapa canal → fonte de grade: mi.tv, meuguia.tv...) e o [iptv-org/epg](https://github.com/iptv-org/epg) usa isso pra gerar a grade (`guide.xml`).

## Créditos e licença

- Dados agregados do [iptv-org](https://github.com/iptv-org/iptv) (Unlicense) e do Pluto TV Brasil. Grade (EPG) via [iptv-org/epg](https://github.com/iptv-org/epg).
- Nenhum stream é hospedado aqui: os links apontam direto pra fonte pública de cada emissora.
