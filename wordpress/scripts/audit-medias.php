<?php
/**
 * Audit et reparation des attachments dont le fichier est absent du disque.
 *
 * A lancer en SSH sur l'hebergement, depuis la racine WordPress :
 *
 *   # 1. Inventaire seul, n'ecrit rien
 *   wp eval-file wordpress/scripts/audit-medias.php
 *
 *   # 2. Applique les corrections de base pour les cas recuperables
 *   wp eval-file wordpress/scripts/audit-medias.php -- --apply
 *
 * Le mode par defaut est un inventaire en lecture seule. Rien n'est ecrit
 * sans --apply.
 *
 * Ce que le script traite
 * ----------------------
 * Cas A, recuperable : la base pointe vers un fichier absent, mais le meme
 * nom existe sur le disque sous une autre extension. Typiquement une entree
 * renommee en .webp alors que le fichier est reste en .png ou .jpg. Le script
 * corrige _wp_attached_file, les noms des tailles derivees dans
 * _wp_attachment_metadata, et post_mime_type.
 *
 * Cas B, perdu : ni le fichier declare ni aucune variante n'existe. Le script
 * ne fait que le signaler. Un fichier absent du disque ne se reconstruit pas
 * depuis la base, il faut le restaurer depuis une sauvegarde.
 *
 * Sortie
 * ------
 * Deux CSV a la racine des uploads :
 *   audit-medias-recuperables.csv
 *   audit-medias-perdus.csv
 */

if ( ! defined( 'WP_CLI' ) || ! WP_CLI ) {
	fwrite( STDERR, "A lancer via WP-CLI : wp eval-file " . basename( __FILE__ ) . "\n" );
	return;
}

$appliquer = in_array( '--apply', (array) ( $args ?? [] ), true )
	|| in_array( '--apply', array_slice( $GLOBALS['argv'] ?? [], 1 ), true );

$extensions = [ 'webp', 'jpg', 'jpeg', 'png', 'gif', 'avif' ];
$mime_par_ext = [
	'webp' => 'image/webp',
	'jpg'  => 'image/jpeg',
	'jpeg' => 'image/jpeg',
	'png'  => 'image/png',
	'gif'  => 'image/gif',
	'avif' => 'image/avif',
];

$uploads  = wp_get_upload_dir();
$base_dir = $uploads['basedir'];

$ids = get_posts( [
	'post_type'      => 'attachment',
	'post_status'    => 'inherit',
	'posts_per_page' => -1,
	'fields'         => 'ids',
	'post_mime_type' => 'image',
] );

WP_CLI::log( sprintf( '%d attachments image a verifier. Mode : %s.',
	count( $ids ), $appliquer ? 'APPLICATION' : 'inventaire seul' ) );

$recuperables = [];
$perdus       = [];
$corriges     = 0;

foreach ( $ids as $id ) {
	$relatif = get_post_meta( $id, '_wp_attached_file', true );
	if ( ! $relatif ) {
		continue;
	}

	$absolu = $base_dir . '/' . $relatif;
	if ( file_exists( $absolu ) ) {
		continue;
	}

	// Le fichier declare est absent. On cherche le meme nom sous une autre extension.
	$sans_ext = preg_replace( '/\.[A-Za-z0-9]+$/', '', $relatif );
	$ext_actuelle = strtolower( pathinfo( $relatif, PATHINFO_EXTENSION ) );

	$trouvee = null;
	foreach ( $extensions as $ext ) {
		if ( $ext === $ext_actuelle ) {
			continue;
		}
		if ( file_exists( $base_dir . '/' . $sans_ext . '.' . $ext ) ) {
			$trouvee = $ext;
			break;
		}
	}

	$ligne = [ $id, get_the_title( $id ), $relatif, get_post_mime_type( $id ) ];

	if ( null === $trouvee ) {
		$perdus[] = $ligne;
		continue;
	}

	$nouveau_relatif = $sans_ext . '.' . $trouvee;
	$ligne[]         = $nouveau_relatif;
	$recuperables[]  = $ligne;

	if ( ! $appliquer ) {
		continue;
	}

	// --- corrections ---
	update_post_meta( $id, '_wp_attached_file', $nouveau_relatif );

	$meta = wp_get_attachment_metadata( $id );
	if ( is_array( $meta ) ) {
		$meta['file'] = $nouveau_relatif;

		if ( ! empty( $meta['sizes'] ) && is_array( $meta['sizes'] ) ) {
			foreach ( $meta['sizes'] as $nom => $taille ) {
				if ( empty( $taille['file'] ) ) {
					continue;
				}
				$candidat = preg_replace( '/\.[A-Za-z0-9]+$/', '.' . $trouvee, $taille['file'] );
				$dossier  = dirname( $base_dir . '/' . $nouveau_relatif );

				// On ne renomme la taille que si le fichier correspondant existe
				// vraiment. Sinon on retire la taille : une taille qui pointe
				// dans le vide fait echouer srcset.
				if ( file_exists( $dossier . '/' . $candidat ) ) {
					$meta['sizes'][ $nom ]['file'] = $candidat;
					$meta['sizes'][ $nom ]['mime-type'] = $mime_par_ext[ $trouvee ];
				} else {
					unset( $meta['sizes'][ $nom ] );
				}
			}
		}

		wp_update_attachment_metadata( $id, $meta );
	}

	// post_mime_type doit refleter le fichier reel.
	wp_update_post( [ 'ID' => $id, 'post_mime_type' => $mime_par_ext[ $trouvee ] ] );

	$corriges++;
	WP_CLI::log( sprintf( '  corrige #%d : %s -> %s', $id, $relatif, $nouveau_relatif ) );
}

$ecrire_csv = function ( $nom, $entetes, $lignes ) use ( $base_dir ) {
	$chemin = $base_dir . '/' . $nom;
	$fh     = fopen( $chemin, 'w' );
	if ( ! $fh ) {
		WP_CLI::warning( 'Ecriture impossible : ' . $chemin );
		return;
	}
	fputcsv( $fh, $entetes );
	foreach ( $lignes as $l ) {
		fputcsv( $fh, $l );
	}
	fclose( $fh );
	WP_CLI::log( sprintf( '%s : %d lignes', $chemin, count( $lignes ) ) );
};

$ecrire_csv( 'audit-medias-recuperables.csv',
	[ 'id', 'titre', 'fichier_declare', 'mime_declare', 'fichier_reel' ], $recuperables );
$ecrire_csv( 'audit-medias-perdus.csv',
	[ 'id', 'titre', 'fichier_declare', 'mime_declare' ], $perdus );

WP_CLI::success( sprintf(
	'%d recuperables, %d perdus. %s',
	count( $recuperables ), count( $perdus ),
	$appliquer
		? sprintf( '%d corriges en base.', $corriges )
		: 'Aucune ecriture. Relancer avec --apply pour corriger les recuperables.'
) );
